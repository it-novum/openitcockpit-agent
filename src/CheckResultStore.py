import threading


class CheckResultStore:

    def __init__(self):
        self.check_results = {}
        self.lock = threading.Lock()

    def store(self, key_name: str, data: dict):
        self.lock.acquire()
        self.check_results[key_name] = data
        self.lock.release()

    def get_store(self) -> dict:
        self.lock.acquire()
        data = self.check_results.copy()
        self.lock.release()

        return data
