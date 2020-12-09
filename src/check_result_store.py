import threading


class CheckResultStore:

    def __init__(self):
        self.check_results = {}
        self.custom_check_results = {}

        self.lock = threading.Lock()
        self.custom_lock = threading.Lock()

    def store(self, key_name: str, data: dict):
        self.lock.acquire()
        self.check_results[key_name] = data
        self.lock.release()

    def get_store(self) -> dict:
        self.lock.acquire()
        data = self.check_results.copy()
        self.lock.release()

        return data

    def get_store_for_json_response(self) -> dict:
        data = self.get_store()

        if "agent" not in data:
            return {}

        if "cpu_checks_combined" in data:
            for key in data['cpu_checks_combined'].keys():
                data[key] = data['cpu_checks_combined'][key]

            del data['cpu_checks_combined']

        data['customchecks'] = self.get_custom_check_store()

        return data

    def store_custom_check(self, key_name: str, data: dict):
        self.custom_lock.acquire()
        self.custom_check_results[key_name] = data
        self.custom_lock.release()

    def get_custom_check_store(self) -> dict:
        self.custom_lock.acquire()
        data = self.custom_check_results.copy()
        self.custom_lock.release()

        return data
