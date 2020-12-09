import psutil

from checks.Check import Check
from operating_system import OperatingSystem


class SwapChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "swap"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running swap checks')

        swap = psutil.swap_memory()
        swap = swap._asdict()

        return swap.copy()
