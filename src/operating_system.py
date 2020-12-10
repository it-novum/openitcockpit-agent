import sys


class OperatingSystem:
    _instance = None

    # Singleton magic
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        self._linux = False
        self._windows = False
        self._darwin = False

        if sys.platform == 'win32' or sys.platform == 'win64':
            self._windows = True
        elif sys.platform == 'darwin' or (self.system == 'linux' and 'linux' not in sys.platform):
            self._darwin = True
        else:
            self._linux = True

    @property
    def windows(self):
        return self._windows

    @property
    def linux(self):
        return self._linux

    @property
    def darwin(self):
        return self._darwin

    @property
    def macos(self):
        return self._darwin
