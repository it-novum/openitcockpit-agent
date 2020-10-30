from http.server import BaseHTTPRequestHandler
from src.check_result_store import CheckResultStore


class AgentRequestHandler(BaseHTTPRequestHandler):
    # todo I don't like this very much
    check_store = None  # type: CheckResultStore

    def do_GET(self):
        check_results = self.check_store.get_store()
        print('GET REQUEST BEKOMMEN', check_results['default_checks']['agent']['agent_version'])
