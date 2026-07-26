"""Main agent orchestrator."""
import time
import threading
from typing import List, Dict, Any, Optional
from enum import Enum

import structlog

from ..config.settings import Settings, get_settings
from ..indicators.base import BaseIndicator, WeightReading
from ..indicators.registry import IndicatorRegistry
from ..storage.buffer_manager import BufferManager
from .api_client import LaravelAPIClient
from .normalizer import DataNormalizer
from .heartbeat import HeartbeatManager

logger = structlog.get_logger(__name__)


class AgentState(Enum):
    """Agent operational states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class WeighbridgeAgent:
    """
    Main agent that orchestrates all components.

    Responsibilities:
    - Manage indicator connections
    - Read weights continuously
    - Buffer data when offline
    - Send data to Laravel
    - Handle reconnection logic
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize agent.

        Args:
            config_path: Path to configuration file
        """
        self.settings = get_settings(config_path)
        self.state = AgentState.STOPPED
        self.logger = logger.bind(
            agent_id=self.settings.agent.id,
            agent_name=self.settings.agent.name
        )

        # Initialize components
        self.indicators: List[BaseIndicator] = []
        self.buffer_manager = BufferManager(
            db_path=self.settings.buffer.db_path,
            max_size=self.settings.buffer.max_size
        )

        self.api_client = LaravelAPIClient(
            base_url=self.settings.api.base_url,
            timeout=self.settings.api.timeout,
            retry_config=self.settings.api.retry,
            circuit_breaker_config=self.settings.api.circuit_breaker
        )

        self.heartbeat_manager = HeartbeatManager(
            agent_id=self.settings.agent.id,
            api_client=self.api_client,
            interval=self.settings.agent.heartbeat_interval
        )

        # Threading
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []

        self.logger.info("Weighbridge agent initialized")

    def initialize_indicators(self):
        """Initialize all configured indicators."""
        self.logger.info("Initializing indicators")

        enabled_indicators = self.settings.get_enabled_indicators()

        for ind_config in enabled_indicators:
            try:
                # Create indicator instance using registry
                indicator = IndicatorRegistry.create_indicator(
                    indicator_type=ind_config.type,
                    indicator_id=ind_config.id,
                    name=ind_config.name,
                    config=ind_config.dict()
                )

                if indicator:
                    self.indicators.append(indicator)
                    self.logger.info(
                        "Indicator registered",
                        indicator_id=ind_config.id,
                        type=ind_config.type
                    )
                else:
                    self.logger.error(
                        "Failed to create indicator",
                        indicator_id=ind_config.id
                    )

            except Exception as e:
                self.logger.exception(
                    "Error initializing indicator",
                    indicator_id=ind_config.id,
                    error=str(e)
                )

        self.logger.info(
            "Indicators initialized",
            count=len(self.indicators)
        )

    def connect_indicators(self) -> int:
        """
        Connect all indicators.

        Returns:
            Number of successful connections
        """
        connected = 0
        for indicator in self.indicators:
            try:
                if indicator.connect():
                    connected += 1
                    self.logger.info(
                        "Indicator connected",
                        indicator_id=indicator.indicator_id
                    )
                else:
                    self.logger.warning(
                        "Failed to connect indicator",
                        indicator_id=indicator.indicator_id
                    )
            except Exception as e:
                self.logger.exception(
                    "Error connecting indicator",
                    indicator_id=indicator.indicator_id,
                    error=str(e)
                )

        return connected

    def disconnect_indicators(self):
        """Disconnect all indicators."""
        for indicator in self.indicators:
            try:
                indicator.disconnect()
                self.logger.info(
                    "Indicator disconnected",
                    indicator_id=indicator.indicator_id
                )
            except Exception as e:
                self.logger.error(
                    "Error disconnecting indicator",
                    indicator_id=indicator.indicator_id,
                    error=str(e)
                )

    def read_indicator(self, indicator: BaseIndicator):
        """
        Continuously read from a single indicator.

        Args:
            indicator: Indicator to read from
        """
        polling_interval = indicator.config.get('polling_interval', 1.0)

        while not self._stop_event.is_set():
            try:
                # Read weight
                reading = indicator.read_weight()

                if reading:
                    # Validate reading
                    if indicator.validate_reading(reading):
                        self._process_reading(reading)
                    else:
                        self.logger.debug(
                            "Invalid reading filtered",
                            indicator_id=indicator.indicator_id
                        )

            except Exception as e:
                self.logger.error(
                    "Error reading indicator",
                    indicator_id=indicator.indicator_id,
                    error=str(e)
                )

            # Sleep for polling interval
            time.sleep(polling_interval)

    def _process_reading(self, reading: WeightReading):
        """
        Process a weight reading.

        Args:
            reading: WeightReading to process
        """
        try:
            # Normalize reading
            normalized = DataNormalizer.prepare_for_api(reading)

            # Try to send to API
            if self.api_client.is_online():
                try:
                    success = self.api_client.send_reading(normalized)
                    if success:
                        self.logger.debug(
                            "Reading sent",
                            indicator_id=reading.indicator_id
                        )
                        return
                except Exception as e:
                    self.logger.warning(
                        "Failed to send reading, buffering",
                        error=str(e)
                    )

            # Buffer if offline or send failed
            self.buffer_manager.add_reading(normalized)
            self.logger.debug(
                "Reading buffered",
                indicator_id=reading.indicator_id
            )

        except Exception as e:
            self.logger.error(
                "Error processing reading",
                error=str(e),
                indicator_id=reading.indicator_id
            )

    def flush_buffer_worker(self):
        """Background worker to flush buffered data."""
        flush_interval = self.settings.buffer.flush_interval
        batch_size = self.settings.buffer.batch_size

        while not self._stop_event.is_set():
            try:
                # Check if API is online
                if self.api_client.is_online():
                    # Get batch of buffered readings
                    batch = self.buffer_manager.get_batch(batch_size)

                    if batch:
                        self.logger.info(
                            "Flushing buffer",
                            batch_size=len(batch)
                        )

                        # Send batch
                        result = self.api_client.send_batch(batch)

                        if result.get('success'):
                            # Mark as sent
                            reading_ids = [r['id'] for r in batch]
                            self.buffer_manager.mark_sent(reading_ids)
                            self.logger.info(
                                "Buffer flushed successfully",
                                count=len(batch)
                            )
                        else:
                            # Mark as failed
                            reading_ids = [r['id'] for r in batch]
                            self.buffer_manager.mark_failed(
                                reading_ids,
                                result.get('error', 'Unknown error')
                            )

            except Exception as e:
                self.logger.error(
                    "Error flushing buffer",
                    error=str(e)
                )

            # Wait before next flush
            time.sleep(flush_interval)

    def start(self):
        """Start the agent."""
        if self.state != AgentState.STOPPED:
            self.logger.warning("Agent already running")
            return

        self.state = AgentState.STARTING
        self.logger.info("Starting weighbridge agent")

        # Initialize indicators
        self.initialize_indicators()

        if not self.indicators:
            self.logger.error("No indicators configured")
            self.state = AgentState.ERROR
            return

        # Connect to indicators
        connected = self.connect_indicators()
        if connected == 0:
            self.logger.error("Failed to connect to any indicators")
            self.state = AgentState.ERROR
            return

        self.logger.info(
            "Connected to indicators",
            connected=connected,
            total=len(self.indicators)
        )

        # Reset stop event
        self._stop_event.clear()

        # Start heartbeat
        self.heartbeat_manager.start()

        # Start reader threads for each indicator
        for indicator in self.indicators:
            if indicator.is_connected():
                thread = threading.Thread(
                    target=self.read_indicator,
                    args=(indicator,),
                    name=f"reader-{indicator.indicator_id}",
                    daemon=True
                )
                thread.start()
                self._threads.append(thread)

        # Start buffer flush worker
        flush_thread = threading.Thread(
            target=self.flush_buffer_worker,
            name="buffer-flush",
            daemon=True
        )
        flush_thread.start()
        self._threads.append(flush_thread)

        self.state = AgentState.RUNNING
        self.logger.info("Weighbridge agent running")

    def stop(self):
        """Stop the agent."""
        if self.state != AgentState.RUNNING:
            self.logger.warning("Agent not running")
            return

        self.state = AgentState.STOPPING
        self.logger.info("Stopping weighbridge agent")

        # Signal threads to stop
        self._stop_event.set()

        # Stop heartbeat
        self.heartbeat_manager.stop()

        # Wait for threads to finish
        for thread in self._threads:
            thread.join(timeout=5)

        # Disconnect indicators
        self.disconnect_indicators()

        # Close connections
        self.buffer_manager.close()
        self.api_client.close()

        self._threads.clear()
        self.state = AgentState.STOPPED
        self.logger.info("Weighbridge agent stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status.

        Returns:
            Status dictionary
        """
        indicator_status = [
            {
                'id': ind.indicator_id,
                'name': ind.name,
                'type': ind.__class__.__name__,
                'connected': ind.is_connected()
            }
            for ind in self.indicators
        ]

        buffer_stats = self.buffer_manager.get_stats()

        return {
            'agent_id': self.settings.agent.id,
            'agent_name': self.settings.agent.name,
            'state': self.state.value,
            'indicators': indicator_status,
            'buffer': buffer_stats,
            'api_online': self.api_client.is_online()
        }

    def run(self):
        """Run agent (blocking)."""
        self.start()

        try:
            # Keep main thread alive
            while self.state == AgentState.RUNNING:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            self.stop()
