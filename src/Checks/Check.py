from src.Config import Config
from src.AgentLog import AgentLog


class Check:

    def __init__(self, config, agent_log, check_store, check_params):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.params = check_params
        self.check_store = check_store

    def run_check(self):
        pass

    def real_check_run(self):
        result = self.run_check()
        1 == 1
        #self.check_store.store(result)
