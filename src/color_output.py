import threading

from datetime import datetime

class ColorOutput:

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

    def __init__(self):
        self.lock = threading.Lock()

    def info(self, msg):
        self.print_with_time(self.CYAN + "[info] " + self.END + msg)

    def error(self, msg):
        self.print_with_time(self.RED + "[error] " + self.END + msg)

    def warning(self, msg):
        self.print_with_time(self.YELLOW + "[warning] " + self.END + msg)

    def debug(self, msg):
        self.print_with_time(self.BLUE + "[DEBUG] " + self.END + msg)

    def verbose(self, msg):
        self.print_with_time(self.PURPLE + "[VERBOSE] " + self.END + msg)

    def print_with_time(self, msg):
        now = datetime.now()
        self.lock.acquire()
        print(self.LIGHT_GRAY + now.strftime("%H:%M:%S") + self.END + " " + msg)
        self.lock.release()
