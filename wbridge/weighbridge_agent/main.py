#!/usr/bin/env python3
"""
Weighbridge Agent - Main Entry Point

Usage:
    python main.py                          # Run in foreground
    python main.py --daemon                 # Run as daemon (Linux)
    python main.py --install-service        # Install as service
    python main.py --uninstall-service      # Uninstall service
    python main.py --config /path/to/config.yaml  # Use custom config
"""
import sys
import argparse
import platform
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from weighbridge_agent.core.agent import WeighbridgeAgent
from weighbridge_agent.utils.logger import setup_logging
from weighbridge_agent.config.settings import get_settings


def run_agent(config_path: str = None):
    """
    Run agent in foreground.

    Args:
        config_path: Path to configuration file
    """
    # Load settings
    settings = get_settings(config_path)

    # Setup logging
    setup_logging(
        log_level=settings.logging.level,
        log_file=settings.logging.file,
        log_format=settings.logging.format,
        console=settings.logging.console
    )

    # Create and run agent
    agent = WeighbridgeAgent(config_path)
    agent.run()


def install_service():
    """Install agent as system service."""
    system = platform.system()

    if system == "Windows":
        from weighbridge_agent.service.windows_service import install_service as win_install
        success = win_install()
        if success:
            print("\nService installed successfully!")
            print("Start with: sc start WeighbridgeAgent")
    elif system == "Linux":
        from weighbridge_agent.service.linux_systemd import install_systemd_service
        success = install_systemd_service()
    else:
        print(f"Service installation not supported on {system}")
        return False

    return success


def uninstall_service():
    """Uninstall agent service."""
    system = platform.system()

    if system == "Windows":
        from weighbridge_agent.service.windows_service import uninstall_service as win_uninstall
        return win_uninstall()
    elif system == "Linux":
        from weighbridge_agent.service.linux_systemd import uninstall_systemd_service
        return uninstall_systemd_service()
    else:
        print(f"Service uninstallation not supported on {system}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Weighbridge Agent - Data collection from weighbridge indicators"
    )

    parser.add_argument(
        '--config',
        '-c',
        help='Path to configuration file',
        default=None
    )

    parser.add_argument(
        '--install-service',
        action='store_true',
        help='Install as system service'
    )

    parser.add_argument(
        '--uninstall-service',
        action='store_true',
        help='Uninstall system service'
    )

    parser.add_argument(
        '--daemon',
        '-d',
        action='store_true',
        help='Run as daemon (Linux only)'
    )

    parser.add_argument(
        '--version',
        '-v',
        action='version',
        version='%(prog)s 1.0.0'
    )

    args = parser.parse_args()

    # Handle service installation
    if args.install_service:
        return 0 if install_service() else 1

    # Handle service uninstallation
    if args.uninstall_service:
        return 0 if uninstall_service() else 1

    # Handle daemon mode (Linux only)
    if args.daemon:
        if platform.system() != "Linux":
            print("Daemon mode only supported on Linux")
            return 1

        print("Starting in daemon mode...")
        # TODO: Implement proper daemonization if needed
        # For now, just run in foreground
        run_agent(args.config)
        return 0

    # Default: run in foreground
    try:
        run_agent(args.config)
        return 0
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
