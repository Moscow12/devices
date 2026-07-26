"""Buffer manager for offline data persistence."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import deque

import structlog
from peewee import SqliteDatabase

from .models import db, BufferedReading, AgentState

logger = structlog.get_logger(__name__)


class BufferManager:
    """
    Manages buffering of weight readings when Laravel is offline.

    Uses dual-mode buffering:
    - In-memory queue for fast access
    - SQLite persistence for recovery
    """

    def __init__(
        self,
        db_path: str = "storage/buffer.db",
        max_size: int = 10000,
        max_retry: int = 3
    ):
        """
        Initialize buffer manager.

        Args:
            db_path: Path to SQLite database
            max_size: Maximum buffer size
            max_retry: Maximum retry attempts
        """
        self.db_path = Path(db_path)
        self.max_size = max_size
        self.max_retry = max_retry
        self._memory_queue: deque = deque(maxlen=max_size)
        self.logger = logger.bind(component="buffer_manager")

        self._initialize_db()

    def _initialize_db(self):
        """Initialize SQLite database and create tables."""
        # Create directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        db.init(str(self.db_path))
        db.connect()
        db.create_tables([BufferedReading, AgentState], safe=True)

        self.logger.info(
            "Buffer database initialized",
            path=str(self.db_path)
        )

        # Load unsent readings into memory queue
        self._load_unsent_to_memory()

    def _load_unsent_to_memory(self):
        """Load unsent readings from database into memory queue."""
        try:
            unsent = (BufferedReading
                     .select()
                     .where(BufferedReading.sent == False)
                     .order_by(BufferedReading.timestamp)
                     .limit(100))

            for reading in unsent:
                self._memory_queue.append(reading.id)

            self.logger.info(
                "Loaded unsent readings",
                count=len(self._memory_queue)
            )
        except Exception as e:
            self.logger.error(
                "Failed to load unsent readings",
                error=str(e)
            )

    def add_reading(self, reading_data: Dict[str, Any]) -> bool:
        """
        Add reading to buffer.

        Args:
            reading_data: Dictionary with reading data

        Returns:
            True if added successfully
        """
        try:
            # Convert metadata to JSON string
            metadata_json = None
            if 'metadata' in reading_data and reading_data['metadata']:
                metadata_json = json.dumps(reading_data['metadata'])

            # Create database record
            reading = BufferedReading.create(
                indicator_id=reading_data['indicator_id'],
                weight=reading_data['weight'],
                unit=reading_data['unit'],
                status=reading_data['status'],
                timestamp=reading_data.get('timestamp', datetime.now()),
                raw_data=reading_data['raw_data'],
                metadata=metadata_json,
                sent=False
            )

            # Add to memory queue
            self._memory_queue.append(reading.id)

            self.logger.debug(
                "Reading buffered",
                indicator_id=reading_data['indicator_id'],
                buffer_size=len(self._memory_queue)
            )

            return True
        except Exception as e:
            self.logger.error(
                "Failed to buffer reading",
                error=str(e)
            )
            return False

    def get_batch(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Get a batch of unsent readings.

        Args:
            batch_size: Number of readings to retrieve

        Returns:
            List of reading dictionaries
        """
        try:
            readings = (BufferedReading
                       .select()
                       .where(
                           (BufferedReading.sent == False) &
                           (BufferedReading.retry_count < self.max_retry)
                       )
                       .order_by(BufferedReading.timestamp)
                       .limit(batch_size))

            batch = []
            for reading in readings:
                data = {
                    'id': reading.id,
                    'indicator_id': reading.indicator_id,
                    'weight': reading.weight,
                    'unit': reading.unit,
                    'status': reading.status,
                    'timestamp': reading.timestamp.isoformat(),
                    'raw_data': reading.raw_data,
                    'metadata': json.loads(reading.metadata) if reading.metadata else None
                }
                batch.append(data)

            return batch
        except Exception as e:
            self.logger.error(
                "Failed to get batch",
                error=str(e)
            )
            return []

    def mark_sent(self, reading_ids: List[int]) -> bool:
        """
        Mark readings as successfully sent.

        Args:
            reading_ids: List of reading IDs

        Returns:
            True if successful
        """
        try:
            query = (BufferedReading
                    .update(sent=True)
                    .where(BufferedReading.id.in_(reading_ids)))
            query.execute()

            # Remove from memory queue
            for rid in reading_ids:
                try:
                    self._memory_queue.remove(rid)
                except ValueError:
                    pass

            self.logger.info(
                "Marked readings as sent",
                count=len(reading_ids)
            )
            return True
        except Exception as e:
            self.logger.error(
                "Failed to mark readings as sent",
                error=str(e)
            )
            return False

    def mark_failed(self, reading_ids: List[int], error_message: str) -> bool:
        """
        Mark readings as failed and increment retry count.

        Args:
            reading_ids: List of reading IDs
            error_message: Error description

        Returns:
            True if successful
        """
        try:
            query = (BufferedReading
                    .update(
                        retry_count=BufferedReading.retry_count + 1,
                        error_message=error_message
                    )
                    .where(BufferedReading.id.in_(reading_ids)))
            query.execute()

            self.logger.warning(
                "Marked readings as failed",
                count=len(reading_ids),
                error=error_message
            )
            return True
        except Exception as e:
            self.logger.error(
                "Failed to mark readings as failed",
                error=str(e)
            )
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.

        Returns:
            Dictionary with buffer stats
        """
        try:
            total = BufferedReading.select().count()
            unsent = BufferedReading.select().where(BufferedReading.sent == False).count()
            failed = BufferedReading.select().where(
                BufferedReading.retry_count >= self.max_retry
            ).count()

            return {
                'total_records': total,
                'unsent': unsent,
                'failed': failed,
                'memory_queue_size': len(self._memory_queue),
                'max_size': self.max_size
            }
        except Exception as e:
            self.logger.error("Failed to get stats", error=str(e))
            return {}

    def cleanup_old_records(self, days: int = 7) -> int:
        """
        Delete successfully sent records older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of records deleted
        """
        try:
            threshold = datetime.now() - timedelta(days=days)
            query = (BufferedReading
                    .delete()
                    .where(
                        (BufferedReading.sent == True) &
                        (BufferedReading.timestamp < threshold)
                    ))
            deleted = query.execute()

            self.logger.info(
                "Cleaned up old records",
                deleted=deleted,
                days=days
            )
            return deleted
        except Exception as e:
            self.logger.error(
                "Failed to cleanup records",
                error=str(e)
            )
            return 0

    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self._memory_queue) == 0

    def close(self):
        """Close database connection."""
        if not db.is_closed():
            db.close()
            self.logger.info("Buffer database closed")
