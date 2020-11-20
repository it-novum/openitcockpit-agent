# This is the entry point of the openITCOCKPIT Monitoring Agent on Linux and macOS
#
# If you want to run the agent on Linux or inside of an IDE like VS Code or PyCharm use the agent_nix.py file
# EVEN if you are using Windows.
# DO NOT USE agent_windows.py in your IDE, it's not made for it!

import signal
import time
from src.agent_generic import AgentService

class LinuxService(AgentService):

    def run(self):
        self.init_service()
        signal.signal(signal.SIGINT, self.main_thread.signal_handler)  # ^C
        signal.signal(signal.SIGTERM, self.main_thread.signal_handler)  # systemctl stop openitcockpit-agent

        # Check for SIGHUP so we can run the Linux Version on Windows inside an IDE
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self.main_thread.signal_handler)  # systemctl reload openitcockpit-agent

        # Endless loop until we get a signal to stop caught by main_thread.signal_handler
        while self.main_thread.loop is True:
            self.main_loop()

            # Do not use signal.pause() because it will block the internen reload which does not send any kernel signals
            # This the win32event.WaitForSingleObject(self.hWaitStop, 5000) way
            signal.sigtimedwait((), 5)

        self.cleanup()

if __name__ == '__main__':
    LinuxService().run()
