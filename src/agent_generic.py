# !/usr/bin/python

#    Copyright 2020, it-novum GmbH
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# supports python >= 3.8
#
# current psutil>=5.5.0,<=5.6.2 limitation due to https://github.com/giampaolo/psutil/issues/1723

from agent_log import AgentLog
from certificates import Certificates
from config import Config
from exceptions import UntrustedAgentException
from main_thread import MainThread
from thread_factory import ThreadFactory
from check_result_store import CheckResultStore
from utils.operating_system import OperatingSystem

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


class AgentService:

    def init_service(self):
        agent_version = "2.0.4"

        self.config = Config(agent_version)
        self.config.load_configuration()

        self.agent_log = AgentLog(Config=self.config)

        self.certificates = Certificates(self.config, self.agent_log)

        self.main_thread = MainThread(self.config, self.agent_log)
        self.check_store = CheckResultStore()
        self.operating_system = OperatingSystem()

        self.thread_factory = ThreadFactory(self.config, self.agent_log, self.main_thread, self.certificates, self.check_store)

        if self.config.autossl:
            try:
                self.certificates.check_auto_certificate()

                # 21600 => check certificate age 4 times a day
                self.autossl_update_interval = 21600
            except UntrustedAgentException:
                self.autossl_update_interval = 60
                self.agent_log.error(
                    'Agent state is untrusted! Set autossl retry interval to 60 seconds'
                )

    def main_loop(self):
        if self.main_thread.spawn_threads:
            mode = 'pull'
            if self.config.is_push_mode:
                mode = 'push'

            self.agent_log.info('Agent version %s is running in %s mode' % (self.config.agent_version, mode))

            # Start the web server in a separate thread
            self.thread_factory.spawn_webserver_thread()

            # Start checks in separate thread
            # self.thread_factory.spawn_checks_thread()

            # Start custom checks in separate thread
            self.thread_factory.spawn_custom_checks_thread()

            if self.config.is_push_mode:
                # Start a new thread to push the check results to the openITCOCKPIT Server
                self.thread_factory.spawn_check_result_push_thread()

                if self.config.autossl:
                    # Start a new thread to check for certificate renewal
                    self.thread_factory.spawn_autossl_thread(self.autossl_update_interval)

            # All threads got spawned
            self.main_thread.spawn_threads = False

        elif self.main_thread.join_threads:
            self.thread_factory.shutdown_all_threads()

            # Set main_thread.join_threads back to False
            # so we are not in an endless loop of spawning and joining threads
            self.main_thread.disable_reload_trigger()

            # All threads are stopped.
            # set spawn_threads back to True so that the next loop will restart all threads (reload)
            # OR something sets main_thread.loop to False so we break the loop (stop or SIGINT)
            self.main_thread.spawn_threads = True

    def cleanup(self):
        # Main thread is not in endless loop anymore - shutdown
        self.agent_log.info("Agent is going to shutdown")

        # Also kill all threads
        self.thread_factory.shutdown_all_threads()

        self.agent_log.info("Agent stopped")
        
    def run_psutil_checks_in_main_thread(self):
        # Define all checks that should get executed by the Agent
        check_params = {
            "timeout": 10
        }

        # Add new checks to the checks array
        # This is the only place where new checks needs to be added
        checks = [
            AgentChecks(self.config, self.agent_log, self.check_store, check_params),
            MemoryChecks(self.config, self.agent_log, self.check_store, check_params),
            SwapChecks(self.config, self.agent_log, self.check_store, check_params),
            UserChecks(self.config, self.agent_log, self.check_store, check_params),
            CpuChecks(self.config, self.agent_log, self.check_store, check_params)
        ]

        if self.config.config.getboolean('default', 'diskstats', fallback=True):
            checks.append(
                DiskChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.config.config.getboolean('default', 'diskio', fallback=True):
            checks.append(
                DiskIoChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.config.config.getboolean('default', 'netio', fallback=True):
            checks.append(
                NetIoChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.config.config.getboolean('default', 'netstats', fallback=True):
            checks.append(
                NetStatsChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.config.config.getboolean('default', 'sensorstats', fallback=True):
            checks.append(
                SensorsChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.config.config.getboolean('default', 'processstats', fallback=True):
            checks.append(
                ProcessChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.operating_system.windows:
            if self.config.config.getboolean('default', 'winservices', fallback=True):
                checks.append(
                    WinServicesChecks(self.config, self.agent_log, self.check_store, check_params)
                )

            if self.config.config.getboolean('default', 'wineventlog', fallback=True):
                checks.append(
                    WinEventlogChecks(self.config, self.agent_log, self.check_store, check_params)
                )

        if self.config.config.getboolean('default', 'dockerstats', fallback=False):
            checks.append(
                DockerChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.config.config.getboolean('default', 'qemustats', fallback=False):
            checks.append(
                QemuChecks(self.config, self.agent_log, self.check_store, check_params)
            )

        if self.operating_system.linux:
            if self.config.config.getboolean('default', 'systemdservices', fallback=True):
                checks.append(
                    SystemdChecks(self.config, self.agent_log, self.check_store, check_params),
                )

        if self.config.config.getboolean('default', 'alfrescostats', fallback=False):
            checks.append(
                AlfrescoChecks(self.config, self.agent_log, self.check_store, check_params),
            )

        self.agent_log.debug('Running integrated checks')
        for check in checks:
            check.real_check_run()