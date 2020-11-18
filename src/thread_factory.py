import concurrent.futures
import threading
import time

from src.checks.alfresco_checks import AlfrescoChecks
from src.checks.default_checks import DefaultChecks
from src.checks.systemd_checks import SystemdChecks
from src.checks.docker_checks import DockerChecks
from src.checks.qemu_checks import QemuChecks
from src.http_server.webserver import Webserver
from src.custom_check import CustomCheck
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.main_thread import MainThread
from src.push_client import PushClient
from src.certificates import Certificates
from src.exceptions.untrusted_agent_exception import UntrustedAgentException
from src.operating_system import OperatingSystem


class ThreadFactory:

    def __init__(self, config, agent_log, main_thread, certificates):
        self.Config: Config = config
        self.agent_log: AgentLog = agent_log
        self.main_thread: MainThread = main_thread
        self.certificates: Certificates = certificates

        self.check_store = CheckResultStore()
        self.operating_system = OperatingSystem()

        self.loop_checks_thread = True
        self.loop_custom_checks_thread = True
        self.loop_check_result_push_thread = True
        self.loop_autossl_thread = True

        if (self.Config.autossl is False):
            # Autossl is disabled
            self.loop_autossl_thread = False

        self.custom_checks = {}

    def shutdown_all_threads(self):
        self.shutdown_webserver_thread()
        self.shutdown_checks_thread()
        self.shutdown_custom_checks_thread()

        try:
            # Try to stop the push thread - only successful if the Agent is running in PUSH Mode
            self.shutdown_check_result_push_thread()
        except Exception:
            pass

        try:
            # Try to stop the certificate renewal thread - only successful if the Agent is running in PUSH Mode
            # with enabled autossl
            self.shutdown_autossl_thread()
        except Exception:
            pass

    def spawn_webserver_thread(self):
        self.webserver = Webserver(self.Config, self.agent_log, self.check_store, self.main_thread, self.certificates)
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
            "timeout": 10
        }

        # Add new checks to the checks array
        # This is the only place where new checks needs to be added
        checks = [
            DefaultChecks(self.Config, self.agent_log, self.check_store, check_params),
        ]

        if (self.Config.config.getboolean('default', 'dockerstats')):
            checks.append(
                DockerChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if (self.Config.config.getboolean('default', 'qemustats')):
            checks.append(
                QemuChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if (self.Config.config.getboolean('default', 'systemdservices') and self.operating_system.isLinux()):
            checks.append(
                SystemdChecks(self.Config, self.agent_log, self.check_store, check_params),
            )

        if (self.Config.config.getboolean('default', 'alfrescostats')):
            checks.append(
                AlfrescoChecks(self.Config, self.agent_log, self.check_store, check_params),
            )

        check_interval = self.Config.config.getint('default', 'interval', fallback=5)
        if (check_interval <= 0):
            self.agent_log.info('check_interval <= 0. Using 5 seconds as check_interval for now.')
            check_interval = 5

        # Run checks on agent startup
        check_interval_counter = check_interval
        while self.loop_checks_thread is True:
            if (check_interval_counter >= check_interval):
                # Execute checks
                # print('run checks')
                check_interval_counter = 1

                # Execute all checks in a separate thread managed by ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    i = 0
                    for check in checks:
                        self.agent_log.debug('Starting new Default Checks Thread %d' % i)
                        i += 1
                        executor.submit(check.real_check_run)
            else:
                # print('Sleep wait for next run ', check_interval_counter, '/', check_interval)
                check_interval_counter += 1
                time.sleep(1)

    def spawn_checks_thread(self):
        # Start a new thread to execute checks
        self.loop_checks_thread = True
        self.checks_thread = threading.Thread(target=self._loop_checks_thread, daemon=True)
        self.checks_thread.start()

    def shutdown_checks_thread(self):
        self.loop_checks_thread = False
        self.checks_thread.join()

    def _loop_custom_checks_thread(self):
        # thread Pool to execute Custom Check Commands
        check_params = {
            "timeout": 10
        }

        self.custom_checks = self.Config.get_custom_checks()
        worker = self.Config.customchecks.getint('default', 'max_worker_threads', fallback=8)

        if worker <= 0:
            worker = 8

        while self.loop_custom_checks_thread is True:

            # Execute all custom checks in a separate thread managed by ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker) as executor:
                i = 0
                for key in self.custom_checks:
                    custom_check = self.custom_checks[key]
                    custom_check['name'] = key

                    if custom_check['next_check'] <= time.time() and custom_check['running'] is False:
                        self.agent_log.debug('Starting new Custom Checks Thread %d' % i)

                        # Mark custom check as running, create a new CustomCheck object
                        # and execute the custom check via the ThreadPool
                        custom_check['running'] = True
                        custom_check_obj = CustomCheck(custom_check, self.check_store, self.agent_log)

                        f = executor.submit(custom_check_obj.execute_check)
                        f.add_done_callback(self.custom_check_thread_is_done_callback)

                        i += 1

                # Custom Checks thread has nothing to do...
                time.sleep(1)

    def custom_check_thread_is_done_callback(self, fn):
        # Execution of a custom check is finished
        check_name = fn.result()
        if check_name in self.custom_checks:
            self.custom_checks[check_name]['running'] = False
            self.custom_checks[check_name]['next_check'] = time.time() + self.custom_checks[check_name]['interval']
            self.custom_checks[check_name]['last_check'] = time.time()

    def spawn_custom_checks_thread(self):
        # Start a new thread to execute checks
        self.loop_custom_checks_thread = True
        self.custom_checks_thread = threading.Thread(target=self._loop_custom_checks_thread, daemon=True)
        self.custom_checks_thread.start()

    def shutdown_custom_checks_thread(self):
        self.loop_custom_checks_thread = False
        self.custom_checks_thread.join()

    def _loop_check_result_push_thread(self):
        push_config = self.Config.push_config
        push_interval = push_config['interval']

        push_interval_counter = 1

        push_client = PushClient(self.Config, self.agent_log, self.check_store, self.certificates)

        while self.loop_check_result_push_thread is True:
            if (push_interval_counter >= push_interval):

                # Push checks results to openITCOCKPIT Server
                push_interval_counter = 1
                push_client.send_check_results()

            else:
                # print('Sleep wait for next run ', push_interval_counter, '/', push_interval)
                push_interval_counter += 1
                time.sleep(1)

    def spawn_check_result_push_thread(self):
        # Start a new thread to handle auto ssl renewal in PUSH Mode
        self.loop_check_result_push_thread = True
        self.check_result_push_thread = threading.Thread(target=self._loop_check_result_push_thread, daemon=True)
        self.check_result_push_thread.start()

    def shutdown_check_result_push_thread(self):
        self.loop_check_result_push_thread = False
        self.check_result_push_thread.join()

    def _loop_autossl_thread(self, interval):
        if interval <= 0:
            interval = 21600

        orig_interval = interval

        check_autossl_counter = 0

        while self.loop_autossl_thread is True:
            if (check_autossl_counter >= interval):

                try:
                    trigger_reload = self.certificates.check_auto_certificate()

                    # No Exception so no new certificate. Use the normal check interval
                    interval = orig_interval
                    check_autossl_counter = 0

                    if trigger_reload is True:
                        self.agent_log.info(
                            'Reloading agent to enable new autossl certificates'
                        )
                        self.main_thread.trigger_reload()

                except UntrustedAgentException:
                    # Agent is not marked as trusted on the openITCOCKPIT Server
                    # Check for a new certificate every minute as long as the agent is not trusted

                    interval = 60
                    check_autossl_counter = 0

                    self.agent_log.error(
                        'Agent state is untrusted! Set autossl retry interval to 60 seconds'
                    )

                except:
                    self.agent_log.error(
                        'Unknown error while pulling agent certificate.'
                    )

            else:
                # print('Sleep wait for next run ', check_autossl_counter, '/', interval)
                check_autossl_counter += 1
                time.sleep(1)

    # 21600
    def spawn_autossl_thread(self, interval=15):
        # 21600 => check certificate age 4 times a day

        # Start a new thread to handle auto ssl renewal in PUSH Mode
        self.loop_autossl_thread = True
        self.autossl_thread = threading.Thread(target=self._loop_autossl_thread, daemon=True, args=(interval,))
        self.autossl_thread.start()

    def shutdown_autossl_thread(self):
        self.loop_autossl_thread = False
        self.autossl_thread.join()