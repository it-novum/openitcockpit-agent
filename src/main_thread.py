import sys
import threading
import signal

from src.config import Config
from src.agent_log import AgentLog


class MainThread:

    def __init__(self, config, agent_log):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log

        self.spawn_threads = True
        self.join_threads = False
        self.loop = True

        self.lock = threading.Lock()

    def signal_handler(self, sig, frame):
        """A custom signal handler to stop the agent if it is called"""

        self.agent_log.info("Got Signal: %s " % sig)

        if sig == signal.SIGINT or sig == signal.SIGTERM:
            self.loop = False

        if hasattr(signal, 'SIGHUP'):
            if sig == signal.SIGHUP:
                self.trigger_reload()

    def trigger_reload(self):
        """Call this function to trigger an reload of all threads"""
        self.lock.acquire()
        self.join_threads = True
        self.lock.release()

    def disable_reload_trigger(self):
        """Call this function to trigger an reload of all threads"""
        self.lock.acquire()
        self.join_threads = False
        self.lock.release()