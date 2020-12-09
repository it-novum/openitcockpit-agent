import psutil

from checks.Check import Check
from operating_system import OperatingSystem


class MemoryChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "memory"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running memory checks')

        memory = psutil.virtual_memory()
        memory = memory._asdict()

        return memory.copy()
