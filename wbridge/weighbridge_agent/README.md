# Weighbridge Agent

Python agent for collecting weight data from weighbridge indicators and sending to Laravel backend.

## Features

✅ **Universal Compatibility** - Works with multiple indicator types (Generic ASCII, Mettler Toledo, Avery, CAS)
✅ **Multi-Transport** - Supports both Serial (RS232/RS485) and TCP/IP connections
✅ **Offline Buffering** - Automatically buffers data when Laravel is offline
✅ **Auto-Recovery** - Reconnects automatically and syncs buffered data
✅ **Service Support** - Runs as Windows Service or Linux systemd service
✅ **Extensible** - Easy to add new indicator types via registry pattern

## Architecture

```
weighbridge_agent/
├── core/              # Main agent logic
├── indicators/        # Indicator parsers (Generic, Avery, CAS, Mettler)
├── transport/         # Serial & TCP communication
├── storage/           # SQLite buffer for offline data
├── config/            # Configuration management
├── utils/             # Logging, validation, retry logic
└── service/           # Windows/Linux service wrappers
```

## Installation

### 1. Install Dependencies

```bash
cd weighbridge_agent
pip install -r requirements.txt
```

### 2. Configure

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
nano .env
```

Edit `config/config.yaml` for indicator settings.

### 3. Run

#### Foreground (Testing)
```bash
python main.py
```

#### As Service

**Linux:**
```bash
sudo python service/linux_systemd.py install
sudo systemctl start weighbridge-agent
sudo journalctl -u weighbridge-agent -f
```

**Windows:**
```cmd
python main.py --install-service
sc start WeighbridgeAgent
```

## Configuration

### config/config.yaml

```yaml
indicators:
  - id: "scale-001"
    name: "Main Truck Scale"
    type: "generic_ascii"  # or mettler_toledo, avery, cas
    enabled: true
    transport:
      type: "serial"       # or tcp
      port: "COM1"         # or /dev/ttyUSB0
      baudrate: 9600
    parser:
      type: "generic_ascii"
      weight_pattern: '\d+\.?\d*'
      unit_pattern: 'kg|lb|ton'
      stable_indicator: 'ST'
    validation:
      min_weight: 0
      max_weight: 100000
      stable_required: true
    polling_interval: 1.0
```

## Adding Custom Indicators

Create a new parser in `indicators/parsers/`:

```python
from ..base import BaseIndicator
from ..registry import IndicatorRegistry

@IndicatorRegistry.register("my_custom_indicator")
class MyCustomIndicator(BaseIndicator):
    def read_weight(self):
        # Your implementation
        pass

    def parse_response(self, raw_data):
        # Your parsing logic
        pass
```

## API Endpoints

The agent expects these Laravel endpoints:

- `POST /api/weighbridge/readings` - Send single reading
- `POST /api/weighbridge/readings/batch` - Send batch
- `POST /api/weighbridge/agent/heartbeat` - Heartbeat
- `GET /api/health` - Health check

## Monitoring

### Check Status
```bash
# Linux
sudo systemctl status weighbridge-agent

# Windows
sc query WeighbridgeAgent
```

### View Logs
```bash
# Linux
sudo journalctl -u weighbridge-agent -f

# Windows
Check: logs/agent.log
```

## Troubleshooting

### Serial Port Access (Linux)
```bash
sudo usermod -a -G dialout $USER
# Logout and login again
```

### Firewall (TCP/IP)
```bash
# Linux
sudo ufw allow from 192.168.1.0/24 to any port 8001

# Windows
netsh advfirewall firewall add rule name="Weighbridge" dir=in action=allow protocol=TCP localport=8001
```

## Development

### Run Tests
```bash
pytest tests/
```

### Code Style
```bash
black weighbridge_agent/
flake8 weighbridge_agent/
```

## License

MIT License

## Support

For issues, contact: support@example.com
