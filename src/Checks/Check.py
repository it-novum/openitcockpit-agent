from src.Config import Config
from src.AgentLog import AgentLog
from src.CheckResultStore import CheckResultStore

class Check:

    def __init__(self, config, agent_log, check_store, check_params):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.params = check_params
        self.check_store: CheckResultStore = check_store

    def run_check(self):
        pass

    def real_check_run(self):
        result = self.run_check()
        self.check_store.store(self.key_name, result)
