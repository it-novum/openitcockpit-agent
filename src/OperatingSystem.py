import sys


class OperatingSystem:
    system = 'linux'

    def __init__(self):
        if sys.platform == 'win32' or sys.platform == 'win64':
            self.system = 'windows'

        if sys.platform == 'darwin' or (self.system == 'linux' and 'linux' not in sys.platform):
            self.system = 'darwin'

    def isWindows(self):
        return self.system == 'windows'

    def isLinux(self):
        return self.system == 'linux'

    def isDarwin(self):
        return self.system == 'darwin'

    def isMacos(self):
        return self.isDarwin()
