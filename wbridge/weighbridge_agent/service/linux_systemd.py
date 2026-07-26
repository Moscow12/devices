"""Linux systemd service generator."""
import os
import sys
from pathlib import Path


SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Weighbridge Agent Service
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
Environment="PATH={venv_path}:$PATH"
ExecStart={python_path} {main_script}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=weighbridge-agent

[Install]
WantedBy=multi-user.target
"""


def generate_systemd_unit(
    install_path: str = "/etc/systemd/system/weighbridge-agent.service",
    user: str = None,
    working_dir: str = None
) -> str:
    """
    Generate systemd service unit file content.

    Args:
        install_path: Path where service will be installed
        user: User to run service as (default: current user)
        working_dir: Working directory (default: current directory)

    Returns:
        Service unit file content
    """
    if user is None:
        user = os.getenv('USER', 'root')

    if working_dir is None:
        working_dir = Path(__file__).parent.parent.parent.absolute()

    # Detect virtual environment
    venv_path = os.path.dirname(sys.executable)
    python_path = sys.executable

    # Main script path
    main_script = Path(working_dir) / "main.py"

    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        user=user,
        working_dir=working_dir,
        venv_path=venv_path,
        python_path=python_path,
        main_script=main_script
    )

    return service_content


def install_systemd_service(user: str = None, working_dir: str = None) -> bool:
    """
    Install systemd service.

    Args:
        user: User to run service as
        working_dir: Working directory

    Returns:
        True if successful, False otherwise
    """
    service_path = "/etc/systemd/system/weighbridge-agent.service"

    # Check if running as root
    if os.geteuid() != 0:
        print("ERROR: Must run as root (use sudo)")
        return False

    try:
        # Generate service content
        service_content = generate_systemd_unit(
            install_path=service_path,
            user=user,
            working_dir=working_dir
        )

        # Write service file
        with open(service_path, 'w') as f:
            f.write(service_content)

        print(f"Service file created: {service_path}")

        # Reload systemd
        os.system("systemctl daemon-reload")
        print("Systemd daemon reloaded")

        # Enable service
        os.system("systemctl enable weighbridge-agent.service")
        print("Service enabled")

        print("\nService installed successfully!")
        print("\nUseful commands:")
        print("  Start:   sudo systemctl start weighbridge-agent")
        print("  Stop:    sudo systemctl stop weighbridge-agent")
        print("  Status:  sudo systemctl status weighbridge-agent")
        print("  Logs:    sudo journalctl -u weighbridge-agent -f")

        return True

    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


def uninstall_systemd_service() -> bool:
    """
    Uninstall systemd service.

    Returns:
        True if successful, False otherwise
    """
    service_path = "/etc/systemd/system/weighbridge-agent.service"

    if os.geteuid() != 0:
        print("ERROR: Must run as root (use sudo)")
        return False

    try:
        # Stop service
        os.system("systemctl stop weighbridge-agent.service")

        # Disable service
        os.system("systemctl disable weighbridge-agent.service")

        # Remove service file
        if os.path.exists(service_path):
            os.remove(service_path)
            print(f"Service file removed: {service_path}")

        # Reload systemd
        os.system("systemctl daemon-reload")
        print("Systemd daemon reloaded")

        print("Service uninstalled successfully")
        return True

    except Exception as e:
        print(f"Failed to uninstall service: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Install:   python linux_systemd.py install [user] [working_dir]")
        print("  Uninstall: python linux_systemd.py uninstall")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'install':
        user = sys.argv[2] if len(sys.argv) > 2 else None
        working_dir = sys.argv[3] if len(sys.argv) > 3 else None
        install_systemd_service(user, working_dir)
    elif command == 'uninstall':
        uninstall_systemd_service()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
