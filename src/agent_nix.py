# This is the entry point of the openITCOCKPIT Monitoring Agent on Linux and macOS
#
# If you want to run the agent on Linux or inside of an IDE like VS Code or PyCharm use the agent_nix.py file
# EVEN if you are using Windows.
# DO NOT USE agent_windows.py in your IDE, it's not made for it!

import signal
import time
import faulthandler
import os

from agent_generic import AgentService


class LinuxService(AgentService):

    def run(self):
        log_file = '/tmp/faulthandler.log'
        fd = open(log_file, 'a')
        faulthandler.enable(file=fd, all_threads=True)
        faulthandler.dump_traceback_later(
            timeout=10,
            repeat=True,
            file=fd
        )

        self.init_service()
        signal.signal(signal.SIGINT, self.main_thread.signal_handler)  # ^C
        signal.signal(signal.SIGTERM, self.main_thread.signal_handler)  # systemctl stop openitcockpit-agent

        # Check for SIGHUP so we can run the Linux Version on Windows inside an IDE
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self.main_thread.signal_handler)  # systemctl reload openitcockpit-agent

        check_interval = self.config.config.getint('default', 'interval', fallback=5)
        if check_interval <= 0:
            self.agent_log.info('check_interval <= 0. Using 5 seconds as check_interval for now.')
            check_interval = 5

        # Run checks on agent startup
        check_interval_counter = check_interval

        # Endless loop until we get a signal to stop caught by main_thread.signal_handler
        while self.main_thread.loop:
            self.main_loop()

            if check_interval_counter >= check_interval:
                # Execute checks
                check_interval_counter = 1
                self.run_psutil_checks_in_main_thread()
            else:
                check_interval_counter += 1

            # Do not use signal.pause() because it will block the internal reload which does not send any kernel signals
            # This the win32event.WaitForSingleObject(self.hWaitStop, 5000) way
            if hasattr(signal, 'sigtimedwait'):
                signal.sigtimedwait((), 1)
            else:
                # macOS has no signal.sigtimedwait
                time.sleep(1)

        self.cleanup()


if __name__ == '__main__':
    LinuxService().run()
