from agent_log import AgentLog
from check_result_store import CheckResultStore
from config import Config
from utils.operating_system import OperatingSystem
from copy import deepcopy


class DefaultCheck:

    def __init__(self, config, agent_log, check_store, check_params):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.check_params = check_params
        self.check_store: CheckResultStore = check_store
        self.operating_system = OperatingSystem()
        self.key_name = None

    def run_check(self):
        return {}

    def real_check_run(self):
        result = self.run_check()
        self.check_store.store(self.key_name, deepcopy(result))

    def wrapdiff(self, last, curr):
        """ Function to calculate the difference between last and curr

            If last > curr, try to guess the boundary at which the value must have wrapped
            by trying the maximum values of 64, 32 and 16 bit signed and unsigned ints.
        """

        if last <= curr:
            return float(curr - last)

        boundary = None
        for chkbound in (64, 63, 32, 31, 16, 15):
            if last > 2 ** chkbound:
                break
            boundary = chkbound
        if boundary is None:
            raise ArithmeticError("Couldn't determine boundary")
        return float(2 ** boundary - last + curr)
