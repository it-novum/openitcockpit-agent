from datetime import datetime

from src.color_output import ColorOutput


class AgentLog:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    LIGHT_GRAY = '\033[37m'
    END = '\033[0m'

    # todo add log level (info, error, warning, verbose etc)
    # todo write to log file
    def __init__(self, Config):
        self.Config = Config
        self.ColorOutput = ColorOutput()

    def print_verbose(self, msg, more_on_stacktrace):
        """Function to print verbose output uniformly and prevent double verbose output at the same time

        Print verbose output and add stacktrace hint if requested.
        Uses a lock to prevent duplicate verbose output at the same time,
        which would result in one of the outputs not being displayed.

        Parameters
        ----------
        msg
            Message string
        more_on_stacktrace
            Boolean to decide whether the stacktrace hint will be printed or not

        """
        print(msg)

        # with print_lock:
        #    if self.Config.verbose:
        #        print(msg)
        #    if not self.Config.stacktrace and more_on_stacktrace and self.Config.verbose:
        #        print("Enable --stacktrace to get more information.")

    def print_verbose_without_lock(self, msg, more_on_stacktrace):
        """Function to directly print verbose output uniformly

        Print verbose output and add stacktrace hint if requested.

        Parameters
        ----------
        msg
            Message string
        more_on_stacktrace
            Boolean to decide whether the stacktrace hint will be printed or not

        """
        if self.Config.verbose:
            self.ColorOutput.verbose(msg)
        if not self.Config.stacktrace and more_on_stacktrace and self.Config.verbose:
            self.ColorOutput.info('Enable --stacktrace to get more information.')

    def info(self, msg):
        self.ColorOutput.info(msg)

    def error(self, msg):
        self.ColorOutput.error(msg)

    def warning(self, msg):
        self.ColorOutput.warning(msg)

    def debug(self, msg):
        self.ColorOutput.debug(msg)

    def verbose(self, msg):
        # todo remove this if
        if "is not allowing us to" in msg:
            return

        self.ColorOutput.verbose(msg)
