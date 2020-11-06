import concurrent.futures
import threading
import time

from src.checks.default_checks import DefaultChecks
from src.checks.systemd_checks import SystemdChecks
from src.checks.docker_checks import DockerChecks
from src.http_server.webserver import Webserver
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.main_thread import MainThread


class ThreadFactory:

    def __init__(self, config, agent_log, main_thread):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.main_thread: MainThread = main_thread

        self.check_store = CheckResultStore()

        self.loop_checks_thread = True
        self.loop_custm_checks_thread = True
        self.loop_autossl_thread = True

        if(self.Config.autossl is False):
            #Autossl is disabled
            self.loop_autossl_thread = False

    def shutdown_all_threads(self):
        self.shutdown_webserver_thread()
        self.shutdown_checks_thread()

    def spawn_webserver_thread(self):
        self.webserver = Webserver(self.Config, self.agent_log, self.check_store, self.main_thread)
        self.webserver.start_webserver()

        # Start the web server in a separate thread
        self.webserver_thread = threading.Thread(target=self.webserver.httpd.serve_forever, daemon=True)
        self.webserver_thread.start()

    def shutdown_webserver_thread(self):
        self.webserver.httpd.shutdown()
        self.webserver_thread.join()

    def _loop_checks_thread(self):
        # Define all checks that should get executed by the Agent
        check_params = {
            "timeout": 5
        }

        # todo implment configuration to disable checks
        checks = [
            DefaultChecks(self.Config, self.agent_log, self.check_store, check_params),
            SystemdChecks(self.Config, self.agent_log, self.check_store, check_params),
            DockerChecks(self.Config, self.agent_log, self.check_store, check_params)
        ]

        check_interval = self.Config.config.getint('default', 'interval', fallback=5)
        if (check_interval <= 0):
            self.agent_log.info('check_interval <= 0. Using 5 seconds as check_interval for now.')
            check_interval = 5

        # Run checks on agent startup
        check_interval_counter = check_interval
        while self.loop_checks_thread is True:
            if (check_interval_counter >= check_interval):
                # Execute checks
                print('run checks')
                check_interval_counter = 1

                # Execute all checks in a separate thread managed by ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    i = 0
                    for check in checks:
                        print('Starting new Thread %d', i)
                        i += 1
                        executor.submit(check.real_check_run)
            else:
                print('Sleep wait for next run ', check_interval_counter, '/', check_interval)
                check_interval_counter += 1
                time.sleep(1)

    def spawn_checks_thread(self):
        # Start a new thread to execute checks
        self.checks_thread = threading.Thread(target=self._loop_checks_thread, daemon=True)
        self.checks_thread.start()

    def shutdown_checks_thread(self):
        self.loop_checks_thread = False
        self.webserver_thread.join()

    def _loop_autossl_thread(self):
        # Define all checks that should get executed by the Agent
        check_params = {
            "timeout": 5
        }

        # todo implment configuration to disable checks
        checks = [
            DefaultChecks(self.Config, self.agent_log, self.check_store, check_params),
            SystemdChecks(self.Config, self.agent_log, self.check_store, check_params),
            DockerChecks(self.Config, self.agent_log, self.check_store, check_params)
        ]

        check_interval = self.Config.config.getint('default', 'interval', fallback=5)
        if (check_interval <= 0):
            self.agent_log.info('check_interval <= 0. Using 5 seconds as check_interval for now.')
            check_interval = 5

        # Run checks on agent startup
        check_interval_counter = check_interval
        while self.loop_autossl_thread is True:
            if (check_interval_counter >= check_interval):
                # Execute checks
                print('run checks')
                check_interval_counter = 1

                # Execute all checks in a separate thread managed by ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    i = 0
                    for check in checks:
                        print('Starting new Thread %d', i)
                        i += 1
                        executor.submit(check.real_check_run)
            else:
                print('Sleep wait for next run ', check_interval_counter, '/', check_interval)
                check_interval_counter += 1
                time.sleep(1)

    def spawn_autossl_thread(self):
        # Start a new thread to handle auto ssl renewal
        self.autossl_thread = threading.Thread(target=self._loop_autossl_thread, daemon=True)
        self.autossl_thread.start()

    def shutdown_autossl_thread(self):
        self.loop_autossl_thread = False
        self.autossl_thread.join()
