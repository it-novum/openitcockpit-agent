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

    def get_store_for_json_response(self) -> dict:
        data = self.get_store()

        # Add all default checks to json (base json structure)
        response = data['default_checks']
        for key in data.keys():
            if (key != 'default_checks'):
                # Add all additional checks like qemu, systemd, docker etc...
                response[key] = data[key]

        return response
