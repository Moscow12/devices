"""Laravel API client with retry and circuit breaker."""
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import requests
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time in seconds before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False

    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        self.is_open = False
        self.last_failure_time = None

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count
            )

    def can_request(self) -> bool:
        """Check if requests are allowed."""
        if not self.is_open:
            return True

        # Check if timeout has elapsed
        if self.last_failure_time:
            elapsed = datetime.now() - self.last_failure_time
            if elapsed.total_seconds() >= self.timeout:
                logger.info("Circuit breaker attempting to close")
                self.is_open = False
                self.failure_count = 0
                return True

        return False


class LaravelAPIClient:
    """Client for communicating with Laravel backend API."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        retry_config: Optional[Dict[str, int]] = None,
        circuit_breaker_config: Optional[Dict[str, int]] = None
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL of Laravel API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            retry_config: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('LARAVEL_API_KEY', '')
        self.timeout = timeout
        self.logger = logger.bind(component="api_client")

        # Setup retry configuration
        retry_config = retry_config or {}
        self.max_retry = retry_config.get('max_attempts', 5)
        self.retry_delay = retry_config.get('delay', 5)

        # Setup circuit breaker
        cb_config = circuit_breaker_config or {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get('failure_threshold', 5),
            timeout=cb_config.get('timeout', 60)
        )

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'WeighbridgeAgent/1.0'
        })

    def _check_circuit_breaker(self):
        """Check if circuit breaker allows requests."""
        if not self.circuit_breaker.can_request():
            raise ConnectionError("Circuit breaker is open")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException,))
    )
    def send_reading(self, reading: Dict[str, Any]) -> bool:
        """
        Send a single weight reading to Laravel.

        Args:
            reading: Reading data dictionary

        Returns:
            True if successful, False otherwise
        """
        self._check_circuit_breaker()

        try:
            response = self.session.post(
                f"{self.base_url}/weighbridge/readings",
                json=reading,
                timeout=self.timeout
            )
            response.raise_for_status()

            self.circuit_breaker.record_success()
            self.logger.info(
                "Reading sent successfully",
                indicator_id=reading.get('indicator_id')
            )
            return True

        except requests.exceptions.RequestException as e:
            self.circuit_breaker.record_failure()
            self.logger.error(
                "Failed to send reading",
                error=str(e),
                indicator_id=reading.get('indicator_id')
            )
            raise

    def send_batch(self, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send batch of readings to Laravel.

        Args:
            readings: List of reading dictionaries

        Returns:
            Dictionary with success/failure counts
        """
        self._check_circuit_breaker()

        try:
            response = self.session.post(
                f"{self.base_url}/weighbridge/readings/batch",
                json={'readings': readings},
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            self.circuit_breaker.record_success()

            self.logger.info(
                "Batch sent successfully",
                count=len(readings),
                response=result
            )
            return result

        except requests.exceptions.RequestException as e:
            self.circuit_breaker.record_failure()
            self.logger.error(
                "Failed to send batch",
                error=str(e),
                count=len(readings)
            )
            return {
                'success': False,
                'error': str(e),
                'processed': 0,
                'failed': len(readings)
            }

    def send_heartbeat(self, agent_data: Dict[str, Any]) -> bool:
        """
        Send agent heartbeat to Laravel.

        Args:
            agent_data: Agent status data

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.base_url}/weighbridge/agent/heartbeat",
                json=agent_data,
                timeout=10
            )
            response.raise_for_status()

            self.logger.debug("Heartbeat sent")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.warning(
                "Failed to send heartbeat",
                error=str(e)
            )
            return False

    def get_config(self) -> Optional[Dict[str, Any]]:
        """
        Fetch configuration from Laravel.

        Returns:
            Configuration dictionary or None
        """
        try:
            response = self.session.get(
                f"{self.base_url}/weighbridge/agent/config",
                timeout=self.timeout
            )
            response.raise_for_status()

            config = response.json()
            self.logger.info("Configuration fetched")
            return config

        except requests.exceptions.RequestException as e:
            self.logger.error(
                "Failed to fetch config",
                error=str(e)
            )
            return None

    def test_connection(self) -> bool:
        """
        Test connection to Laravel API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            response.raise_for_status()

            self.logger.info("Connection test successful")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(
                "Connection test failed",
                error=str(e)
            )
            return False

    def is_online(self) -> bool:
        """
        Quick check if API is reachable.

        Returns:
            True if online, False otherwise
        """
        if not self.circuit_breaker.can_request():
            return False

        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def close(self):
        """Close session."""
        self.session.close()
        self.logger.info("API client closed")
