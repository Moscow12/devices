"""Windows Service wrapper for the agent."""
import sys
import os

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    WINDOWS_SERVICE_AVAILABLE = True
except ImportError:
    WINDOWS_SERVICE_AVAILABLE = False

import structlog

from ..core.agent import WeighbridgeAgent
from ..utils.logger import setup_logging

logger = structlog.get_logger(__name__)


if WINDOWS_SERVICE_AVAILABLE:
    class WeighbridgeService(win32serviceutil.ServiceFramework):
        """Windows Service wrapper."""

        _svc_name_ = "WeighbridgeAgent"
        _svc_display_name_ = "Weighbridge Agent Service"
        _svc_description_ = "Python agent for weighbridge data collection"

        def __init__(self, args):
            """Initialize service."""
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent: WeighbridgeAgent = None

        def SvcStop(self):
            """Handle stop request."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

            if self.agent:
                self.agent.stop()

            self.ReportServiceStatus(win32service.SERVICE_STOPPED)

        def SvcDoRun(self):
            """Service main loop."""
            try:
                # Setup logging
                setup_logging(
                    log_level="INFO",
                    log_file="logs/service.log",
                    log_format="json",
                    console=False
                )

                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, '')
                )

                # Initialize and start agent
                self.agent = WeighbridgeAgent()
                self.agent.start()

                # Wait for stop signal
                win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

            except Exception as e:
                servicemanager.LogErrorMsg(f"Service error: {str(e)}")
                logger.exception("Service error", error=str(e))


def install_service():
    """Install Windows service."""
    if not WINDOWS_SERVICE_AVAILABLE:
        print("pywin32 not available. Cannot install Windows service.")
        return False

    try:
        win32serviceutil.InstallService(
            WeighbridgeService._svc_name_,
            WeighbridgeService._svc_display_name_,
            WeighbridgeService._svc_description_,
            startType=win32service.SERVICE_AUTO_START
        )
        print(f"Service '{WeighbridgeService._svc_display_name_}' installed successfully")
        return True
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


def uninstall_service():
    """Uninstall Windows service."""
    if not WINDOWS_SERVICE_AVAILABLE:
        print("pywin32 not available.")
        return False

    try:
        win32serviceutil.RemoveService(WeighbridgeService._svc_name_)
        print(f"Service '{WeighbridgeService._svc_display_name_}' uninstalled successfully")
        return True
    except Exception as e:
        print(f"Failed to uninstall service: {e}")
        return False


def start_service():
    """Start Windows service."""
    if not WINDOWS_SERVICE_AVAILABLE:
        return False

    try:
        win32serviceutil.StartService(WeighbridgeService._svc_name_)
        print("Service started")
        return True
    except Exception as e:
        print(f"Failed to start service: {e}")
        return False


def stop_service():
    """Stop Windows service."""
    if not WINDOWS_SERVICE_AVAILABLE:
        return False

    try:
        win32serviceutil.StopService(WeighbridgeService._svc_name_)
        print("Service stopped")
        return True
    except Exception as e:
        print(f"Failed to stop service: {e}")
        return False


if __name__ == '__main__':
    if WINDOWS_SERVICE_AVAILABLE:
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(WeighbridgeService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(WeighbridgeService)
    else:
        print("This module requires pywin32. Install with: pip install pywin32")
