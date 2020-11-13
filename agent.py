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

from src.operating_system import OperatingSystem
from src.main_thread import MainThread
from src.config import Config
from src.agent_log import AgentLog
from src.certificates import Certificates
from src.thread_factory import ThreadFactory

if __name__ == '__main__':
    agentVersion = "2.0.0"

    config = Config(agentVersion)
    config.load_configuration()

    agent_log = AgentLog(Config=Config)

    certificates = Certificates(config, agent_log)

    main_thread = MainThread(config, agent_log)
    signal.signal(signal.SIGINT, main_thread.signal_handler)  # ^C
    signal.signal(signal.SIGTERM, main_thread.signal_handler)  # systemctl stop openitcockpit-agent
    signal.signal(signal.SIGHUP, main_thread.signal_handler)  # systemctl reload openitcockpit-agent

    thread_factory = ThreadFactory(config, agent_log, main_thread, certificates)
    operating_system = OperatingSystem()

    if config.autossl is True:
        pass # todo implement me
        #certificates.check_auto_certificate()

    # Endless loop until we get a signal to stop caught by main_thread.signal_handler
    while main_thread.loop is True:
        if main_thread.spawn_threads is True:
            mode = 'pull'
            if config.is_push_mode:
                mode = 'push'

            agent_log.info('Agent is running in %s mode' % mode)

            # Start the web server in a separate thread
            thread_factory.spawn_webserver_thread()

            # Start checks in separate thread
            thread_factory.spawn_checks_thread()

            # Start custom checks in separate thread
            thread_factory.spawn_custom_checks_thread()

            if config.is_push_mode:
                # Start a new thread to push the check results to the openITCOCKPIT Server
                thread_factory.spawn_check_result_push_thread()

                if config.autossl:
                    # Start a new thread to check for certificate renewal
                    thread_factory.spawn_autossl_thread()

            # All threads got spawned
            main_thread.spawn_threads = False

        elif main_thread.join_threads is True:
            thread_factory.shutdown_all_threads()

            # Set main_thread.join_threads back to True
            # so we are not in an endloess loop of spawning and joining threads
            main_thread.disable_reload_trigger()

            # All threads are stopped.
            # set spawn_threads back to True so that the next loop will restart all threads (reload)
            # OR something sets main_thread.loop to False so we break the loop (stop or SIGINT)
            main_thread.spawn_threads = True

        else:
            # Noting to do - all work is done by the created threads above
            # just hanging around and waiting for signals like SIGINT and sleep to save up CPU time
            time.sleep(0.1)

    # Main thread is not in endless loop anymore - shutdown
    agent_log.info("Agent is going to shutdown")

    # Also kill all threads
    thread_factory.shutdown_all_threads()

    agent_log.info("Agent stopped")
