from src.config import Config


class AgentLog:
    Config = None  # type: Config

    # todo add log level (info, error, warning, verbose etc)
    def __init__(self, Config):
        self.Config = Config

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
            print(msg)
        if not self.Config.stacktrace and more_on_stacktrace and self.Config.verbose:
            print("Enable --stacktrace to get more information.")

    def info(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def debug(self, msg):
        print(msg)

    def verbose(self, msg):
        #print(msg)
        pass