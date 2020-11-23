
#!/usr/bin/python

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

import concurrent.futures
import signal
import threading
import time

from src.main_thread import MainThread
from src.config import Config
from src.agent_log import AgentLog
from src.certificates import Certificates
from src.thread_factory import ThreadFactory

class AgentService:

    def init_service(self):
        agentVersion = "2.0.0"

        self.config = Config(agentVersion)
        self.config.load_configuration()

        self.agent_log = AgentLog(Config=self.config)

        self.certificates = Certificates(self.config, self.agent_log)

        self.main_thread = MainThread(self.config, self.agent_log)

        self.thread_factory = ThreadFactory(self.config, self.agent_log, self.main_thread, self.certificates)

        if self.config.autossl is True:
            self.certificates.check_auto_certificate()

    def main_loop(self):
        if self.main_thread.spawn_threads is True:
            mode = 'pull'
            if self.config.is_push_mode:
                mode = 'push'

            self.agent_log.info('Agent is running in %s mode' % mode)

            # Start the web server in a separate thread
            self.thread_factory.spawn_webserver_thread()

            # Start checks in separate thread
            self.thread_factory.spawn_checks_thread()

            # Start custom checks in separate thread
            self.thread_factory.spawn_custom_checks_thread()

            if self.config.is_push_mode:
                # Start a new thread to push the check results to the openITCOCKPIT Server
                self.thread_factory.spawn_check_result_push_thread()

                if self.config.autossl:
                    # Start a new thread to check for certificate renewal
                    self.thread_factory.spawn_autossl_thread()

            # All threads got spawned
            self.main_thread.spawn_threads = False

        elif self.main_thread.join_threads is True:
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


