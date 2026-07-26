"""Database models for buffer storage."""
from datetime import datetime
from peewee import (
    Model,
    SqliteDatabase,
    CharField,
    FloatField,
    DateTimeField,
    TextField,
    BooleanField,
    IntegerField
)

# Database will be initialized by buffer manager
db = SqliteDatabase(None)


class BaseModel(Model):
    """Base model with database binding."""
    class Meta:
        database = db


class BufferedReading(BaseModel):
    """Model for buffered weight readings."""
    indicator_id = CharField(index=True)
    weight = FloatField()
    unit = CharField()
    status = CharField()
    timestamp = DateTimeField(default=datetime.now, index=True)
    raw_data = TextField()
    metadata = TextField(null=True)  # JSON string
    retry_count = IntegerField(default=0)
    sent = BooleanField(default=False, index=True)
    error_message = TextField(null=True)

    class Meta:
        table_name = 'buffered_readings'
        indexes = (
            (('sent', 'timestamp'), False),
        )


class AgentState(BaseModel):
    """Model for persisting agent state."""
    key = CharField(unique=True, primary_key=True)
    value = TextField()
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'agent_state'
