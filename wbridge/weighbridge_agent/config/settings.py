"""Configuration management for weighbridge agent."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class TransportConfig(BaseSettings):
    """Transport configuration."""
    type: str  # serial, tcp, modbus
    port: Optional[str] = None  # Serial port
    baudrate: Optional[int] = 9600
    bytesize: Optional[int] = 8
    parity: Optional[str] = "N"
    stopbits: Optional[int] = 1
    timeout: Optional[float] = 2.0
    host: Optional[str] = None  # TCP host



class ParserConfig(BaseSettings):
    """Parser configuration."""
    type: str
    weight_pattern: Optional[str] = r'\d+\.?\d*'
    unit_pattern: Optional[str] = r'kg|lb|ton'
    stable_indicator: Optional[str] = None


class ValidationConfig(BaseSettings):
    """Validation rules."""
    min_weight: float = 0.0
    max_weight: float = 999999.0
    stable_required: bool = False


class IndicatorConfig(BaseSettings):
    """Individual indicator configuration."""
    id: str
    name: str
    type: str
    enabled: bool = True
    transport: Dict[str, Any]
    parser: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None
    polling_interval: float = 1.0


class APIConfig(BaseSettings):
    """API client configuration."""
    base_url: str = Field(default="http://localhost:8000/api")
    timeout: int = 30
    retry: Dict[str, int] = {
        "max_attempts": 5,
        "delay": 5,
        "backoff": 2
    }
    circuit_breaker: Dict[str, int] = {
        "failure_threshold": 5,
        "timeout": 60
    }


class BufferConfig(BaseSettings):
    """Buffer configuration."""
    enabled: bool = True
    max_size: int = 10000
    flush_interval: int = 60
    db_path: str = "storage/buffer.db"
    batch_size: int = 100


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    file: str = "logs/agent.log"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    console: bool = True


class AgentConfig(BaseSettings):
    """Main agent configuration."""
    id: str = "weighbridge-001"
    name: str = "Weighbridge Agent"
    version: str = "1.0.0"
    heartbeat_interval: int = 60


class Settings:
    """Main settings manager."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings from YAML and environment."""
        # Load environment variables
        load_dotenv()

        # Determine config path
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Override with environment variables where applicable
        self._apply_env_overrides(config_data)

        # Parse configurations
        self.agent = AgentConfig(**config_data.get('agent', {}))
        self.logging = LoggingConfig(**config_data.get('logging', {}))
        self.api = APIConfig(**config_data.get('api', {}))
        self.buffer = BufferConfig(**config_data.get('buffer', {}))

        # Parse indicators
        self.indicators = [
            IndicatorConfig(**ind)
            for ind in config_data.get('indicators', [])
        ]

        self.monitoring = config_data.get('monitoring', {})

    def _apply_env_overrides(self, config: Dict[str, Any]):
        """Override config with environment variables."""
        # API overrides
        if 'api' in config:
            if os.getenv('LARAVEL_API_URL'):
                config['api']['base_url'] = os.getenv('LARAVEL_API_URL')
            if os.getenv('LARAVEL_API_TIMEOUT'):
                config['api']['timeout'] = int(os.getenv('LARAVEL_API_TIMEOUT'))

        # Agent overrides
        if 'agent' in config:
            if os.getenv('AGENT_ID'):
                config['agent']['id'] = os.getenv('AGENT_ID')
            if os.getenv('AGENT_NAME'):
                config['agent']['name'] = os.getenv('AGENT_NAME')

        # Logging overrides
        if 'logging' in config:
            if os.getenv('LOG_LEVEL'):
                config['logging']['level'] = os.getenv('LOG_LEVEL')
            if os.getenv('LOG_FILE'):
                config['logging']['file'] = os.getenv('LOG_FILE')

        # Buffer overrides
        if 'buffer' in config:
            if os.getenv('BUFFER_DB_PATH'):
                config['buffer']['db_path'] = os.getenv('BUFFER_DB_PATH')

    def get_indicator_by_id(self, indicator_id: str) -> Optional[IndicatorConfig]:
        """Get indicator configuration by ID."""
        for indicator in self.indicators:
            if indicator.id == indicator_id:
                return indicator
        return None

    def get_enabled_indicators(self) -> List[IndicatorConfig]:
        """Get all enabled indicators."""
        return [ind for ind in self.indicators if ind.enabled]

    def reload(self):
        """Reload configuration from file."""
        self._load_config()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(config_path: Optional[str] = None) -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings(config_path)
    return _settings


def reload_settings():
    """Reload settings from configuration file."""
    global _settings
    if _settings is not None:
        _settings.reload()
