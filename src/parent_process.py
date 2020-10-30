import sys

from src.config import Config
from src.agent_log import AgentLog


class ParentProcess:

    def __init__(self, config, agent_log):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log

        self.spawn_threads = True
        self.join_threads = False
        self.loop = True

    def signal_handler(self, sig, frame):
        """A custom signal handler to stop the agent if it is called"""

        self.agent_log.info("Got Signal: %s " % sig)
        self.loop = False

