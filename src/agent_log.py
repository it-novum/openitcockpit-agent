import logging
import logging.handlers

from logging.handlers import RotatingFileHandler
from src.color_output import ColorOutput
from datetime import datetime


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
    def __init__(self, Config):
        self.Config = Config
        self.ColorOutput = ColorOutput()

        # keep each logfile ~10MB (10 * 1024 * 1024)
        log_formatter = logging.Formatter('%(asctime)s; %(levelname)s; %(lineno)d; %(message)s')
        logfile_handler = RotatingFileHandler(
            'agent.log',
            mode='a',
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding=None,
            delay=False
        )

        logfile_handler.setFormatter(log_formatter)
        logfile_handler.setLevel(logging.DEBUG)

        self.logfile = logging.getLogger('root')
        self.logfile.setLevel(logging.DEBUG)

        self.logfile.addHandler(logfile_handler)

    def info(self, msg):
        self.ColorOutput.info(msg)
        self.logfile.info(msg)

    def error(self, msg):
        self.ColorOutput.error(msg)
        self.logfile.error(msg)

    def warning(self, msg):
        self.ColorOutput.warning(msg)
        self.logfile.warning(msg)

    def debug(self, msg):
        self.ColorOutput.debug(msg)
        self.logfile.debug(msg)

    def verbose(self, msg):
        # todo replace this with an spam loglevel or so
        if "is not allowing us to" in msg:
            return

        self.ColorOutput.verbose(msg)
        self.ColorOutput.verbose(msg)
