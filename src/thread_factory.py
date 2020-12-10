from concurrent.futures import ThreadPoolExecutor
import threading
import time
import os

from agent_log import AgentLog
from certificates import Certificates
from check_result_store import CheckResultStore
from checks.agent_checks import AgentChecks
from checks.memory_checks import MemoryChecks
from checks.swap_checks import SwapChecks
from checks.user_checks import UserChecks
from checks.cpu_checks import CpuChecks
from checks.disk_checks import DiskChecks
from checks.diskio_checks import DiskIoChecks
from checks.netio_checks import NetIoChecks
from checks.netstats_checks import NetStatsChecks
from checks.sensors_checks import SensorsChecks
from checks.process_checks import ProcessChecks
from checks.win_services_checks import WinServicesChecks
from checks.win_eventlog_checks import WinEventlogChecks
from checks.alfresco_checks import AlfrescoChecks
from checks.docker_checks import DockerChecks
from checks.qemu_checks import QemuChecks
from checks.systemd_checks import SystemdChecks
from config import Config
from custom_check import CustomCheck
from exceptions import UntrustedAgentException
from http_server.webserver_flask import WebserverFlask
from main_thread import MainThread
from utils.operating_system import OperatingSystem
from push_client import PushClient


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

        if not self.Config.autossl:
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
        self.webserver = WebserverFlask(self.Config, self.agent_log, self.check_store, self.main_thread,
                                        self.certificates)
        self.webserver.start_webserver()

        # Start the web server in a separate thread

        self.webserver_thread = threading.Thread(target=self.webserver.srv.serve_forever, daemon=True)
        # self.webserver_thread = threading.Thread(target=self.webserver.loop, daemon=True)
        self.webserver_thread.start()

    def shutdown_webserver_thread(self):
        self.webserver.srv.shutdown()
        # self.webserver.shutdown()
        self.webserver_thread.join()

    def _loop_checks_thread(self):
        # Define all checks that should get executed by the Agent
        check_params = {
            "timeout": 10
        }

        # Add new checks to the checks array
        # This is the only place where new checks needs to be added
        checks = [
            AgentChecks(self.Config, self.agent_log, self.check_store, check_params),
            MemoryChecks(self.Config, self.agent_log, self.check_store, check_params),
            SwapChecks(self.Config, self.agent_log, self.check_store, check_params),
            UserChecks(self.Config, self.agent_log, self.check_store, check_params),
            CpuChecks(self.Config, self.agent_log, self.check_store, check_params)
        ]

        if self.Config.config.getboolean('default', 'diskstats', fallback=True):
            checks.append(
                DiskChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.Config.config.getboolean('default', 'diskio', fallback=True):
            checks.append(
                DiskIoChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.Config.config.getboolean('default', 'netio', fallback=True):
            checks.append(
                NetIoChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.Config.config.getboolean('default', 'netstats', fallback=True):
            checks.append(
                NetStatsChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.Config.config.getboolean('default', 'sensorstats', fallback=True):
            checks.append(
                SensorsChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.Config.config.getboolean('default', 'processstats', fallback=True):
            checks.append(
                ProcessChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.operating_system.windows:
            if self.Config.config.getboolean('default', 'winservices', fallback=True):
                checks.append(
                    WinServicesChecks(self.Config, self.agent_log, self.check_store, check_params)
                )

            if self.Config.config.getboolean('default', 'wineventlog', fallback=True):
                checks.append(
                    WinEventlogChecks(self.Config, self.agent_log, self.check_store, check_params)
                )

        if self.Config.config.getboolean('default', 'dockerstats', fallback=False):
            checks.append(
                DockerChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.Config.config.getboolean('default', 'qemustats', fallback=False):
            checks.append(
                QemuChecks(self.Config, self.agent_log, self.check_store, check_params)
            )

        if self.operating_system.linux:
            if self.Config.config.getboolean('default', 'systemdservices', fallback=True):
                checks.append(
                    SystemdChecks(self.Config, self.agent_log, self.check_store, check_params),
                )

        if self.Config.config.getboolean('default', 'alfrescostats', fallback=False):
            checks.append(
                AlfrescoChecks(self.Config, self.agent_log, self.check_store, check_params),
            )

        check_interval = self.Config.config.getint('default', 'interval', fallback=5)
        if check_interval <= 0:
            self.agent_log.info('check_interval <= 0. Using 5 seconds as check_interval for now.')
            check_interval = 5

        # This is stolen from Pythons ThreadPoolExecutor
        # Use max 32 threads on CPUs with many cores but at least 4 threads on hardware with less cores
        max_workers = min(32, (os.cpu_count() or 1) + 4)

        # Run checks on agent startup
        check_interval_counter = check_interval
        while self.loop_checks_thread:
            if check_interval_counter >= check_interval:
                # Execute checks
                check_interval_counter = 1

                executor = ThreadPoolExecutor()
                i = 0
                for check in checks:
                    self.agent_log.debug('Starting new Thread %d for "%s"' % (i, check.key_name))
                    i += 1
                    executor.submit(check.real_check_run)

                executor.shutdown()

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

        while self.loop_custom_checks_thread:

            # Execute all custom checks in a separate thread managed by ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=worker) as executor:
                i = 0
                for key in self.custom_checks:
                    custom_check = self.custom_checks[key]
                    custom_check['name'] = key

                    if custom_check['next_check'] <= time.time() and not custom_check['running']:
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

        while self.loop_check_result_push_thread:
            if push_interval_counter >= push_interval:

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

        check_autossl_counter = 0

        while self.loop_autossl_thread:
            if check_autossl_counter >= interval:

                try:
                    trigger_reload = self.certificates.check_auto_certificate()

                    # No Exception so no new certificate. Use the normal check interval
                    interval = 21600
                    check_autossl_counter = 0

                    if trigger_reload:
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

    def spawn_autossl_thread(self, interval=21600):
        # 21600 => check certificate age 4 times a day

        # Start a new thread to handle auto ssl renewal in PUSH Mode
        self.loop_autossl_thread = True
        self.autossl_thread = threading.Thread(target=self._loop_autossl_thread, daemon=True, args=(interval,))
        self.autossl_thread.start()

    def shutdown_autossl_thread(self):
        self.loop_autossl_thread = False
        self.autossl_thread.join()
