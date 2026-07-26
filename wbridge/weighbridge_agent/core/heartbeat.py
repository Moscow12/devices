"""Heartbeat and health monitoring."""
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class HeartbeatManager:
    """
    Manages periodic heartbeat to Laravel backend.

    Sends agent status and health information at regular intervals.
    """

    def __init__(
        self,
        agent_id: str,
        api_client,
        interval: int = 60
    ):
        """
        Initialize heartbeat manager.

        Args:
            agent_id: Agent identifier
            api_client: LaravelAPIClient instance
            interval: Heartbeat interval in seconds
        """
        self.agent_id = agent_id
        self.api_client = api_client
        self.interval = interval
        self.logger = logger.bind(component="heartbeat")

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self.start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.heartbeat_count = 0

    def start(self):
        """Start heartbeat thread."""
        if self._running:
            self.logger.warning("Heartbeat already running")
            return

        self.start_time = datetime.now()
        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name="heartbeat",
            daemon=True
        )
        self._thread.start()
        self.logger.info("Heartbeat started", interval=self.interval)

    def stop(self):
        """Stop heartbeat thread."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        self.logger.info("Heartbeat stopped")

    def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self._send_heartbeat()
                self.heartbeat_count += 1
                self.last_heartbeat = datetime.now()
            except Exception as e:
                self.logger.error(
                    "Error sending heartbeat",
                    error=str(e)
                )

            # Wait for next interval
            self._stop_event.wait(self.interval)

    def _send_heartbeat(self):
        """Send heartbeat to API."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        heartbeat_data = {
            'agent_id': self.agent_id,
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'heartbeat_count': self.heartbeat_count,
            'status': 'running'
        }

        try:
            self.api_client.send_heartbeat(heartbeat_data)
        except Exception as e:
            self.logger.debug(
                "Heartbeat send failed",
                error=str(e)
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get heartbeat statistics.

        Returns:
            Statistics dictionary
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            'running': self._running,
            'uptime_seconds': uptime,
            'heartbeat_count': self.heartbeat_count,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'interval': self.interval
        }
