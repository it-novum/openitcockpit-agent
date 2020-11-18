import signal
from src.agent_generic import AgentService

class LinuxService(AgentService):

    def run(self):
        self.init_service()
        signal.signal(signal.SIGINT, self.main_thread.signal_handler)  # ^C
        signal.signal(signal.SIGTERM, self.main_thread.signal_handler)  # systemctl stop openitcockpit-agent
        signal.signal(signal.SIGHUP, self.main_thread.signal_handler)  # systemctl reload openitcockpit-agent

        # Endless loop until we get a signal to stop caught by main_thread.signal_handler
        while self.main_thread.loop is True:
            self.main_loop()
            signal.pause()

        self.cleanup()

if __name__ == '__main__':
    LinuxService().run()
