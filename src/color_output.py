import threading
import sys

from datetime import datetime
from src.operating_system import OperatingSystem

if sys.platform == 'win32' or sys.platform == 'win64':
    import ctypes

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

        operating_system = OperatingSystem()
        if operating_system.isWindows():
            # Enable ANSI color support on Windows 10
            # This requires Windows 10 (1909)
            try:
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                pass

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
