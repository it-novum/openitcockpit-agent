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

from src.checks.default_checks import DefaultChecks
from src.checks.systemd_checks import SystemdChecks
from src.operating_system import OperatingSystem
from src.parent_process import ParentProcess
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.http_server.webserver import Webserver
from src.thread_factory import ThreadFactory

if __name__ == '__main__':
    agentVersion = "2.0.0"

    config = Config(agentVersion)
    config.load_configuration()

    agent_log = AgentLog(Config=Config)

    parent_process = ParentProcess(config, agent_log)
    signal.signal(signal.SIGINT, parent_process.signal_handler)  # ^C
    signal.signal(signal.SIGTERM, parent_process.signal_handler)  # systemctl stop openitcockpit-agent
    # signal.signal(signal.SIGHUP, parent_process.signal_handler)  # systemctl reload openitcockpit-agent

    thread_factory = ThreadFactory(config, agent_log)
    operating_system = OperatingSystem()

    # Endless loop until we get a signal to stop caught by parent_process.signal_handler
    while parent_process.loop is True:
        if parent_process.spawn_threads is True:
            # Start the web server in a separate thread
            thread_factory.spawn_webserver_thread()

            # Start checks separate thread
            thread_factory.spawn_checks_thread()

            # All threads got spawned
            parent_process.spawn_threads = False

        elif parent_process.join_threads is True:
            thread_factory.shutdown_all_threads()

            # All threads are stopped.
            # set spawn_threads back to True so that the next loop will restart all threads (reload)
            # OR something sets parent_process.loop to false so we break the loop (stop or SIGINT)
            parent_process.spawn_threads = True

        else:
            # Noting to do - all work is done by the created threads above
            # just hanging around and waiting for signals like SIGINT and sleep to save up CPU time

            if (operating_system.isWindows() is True):
                # Windows does not have a signal.pause() so we waste a few more cpu cycles.
                time.sleep(0.1)
            else:
                # We can use signal.pause on Linux and macOS
                signal.pause()

    # Main thread is not in endless loop anymore - shutdown
    agent_log.info("Agent is going to shutdown")

    # Also kill all threads
    thread_factory.shutdown_all_threads()

    agent_log.info("Agent stopped")
