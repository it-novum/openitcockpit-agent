import psutil

from checks.default_check import DefaultCheck


class MemoryChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "memory"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running memory checks')

        memory = psutil.virtual_memory()
        memory = memory._asdict()

        return memory
