# This is the entry point of the openITCOCKPIT Monitoring Agent on Windows Systems
# and if the agent is running as an Windows Service.
#
# If you want to run the agent on Linux or inside of an IDE like VS Code or PyCharm use the agent_nix.py file
# EVEN if you are using Windows

from src.agent_generic import AgentService

import servicemanager
import socket
import sys
import win32event
import win32service
import win32serviceutil
import win32timezone


class OITCService(win32serviceutil.ServiceFramework, AgentService):
    _svc_name_ = "openITCOCKPITAgent"
    _svc_display_name_ = "openITCOCKPIT Monitoring Agent"
    _svc_description_ = "openITCOCKPIT Monitoring Agent and remote plugin executor."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        rc = None
        self.init_service()
        while rc != win32event.WAIT_OBJECT_0:
            self.main_loop()
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
        self.cleanup()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(OITCService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(OITCService)
