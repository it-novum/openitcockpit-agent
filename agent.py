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
from src.parent_process import ParentProcess
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore
from src.http_server.webserver import Webserver

if __name__ == '__main__':
    agentVersion = "2.0.0"

    config = Config(agentVersion)
    config.load_configuration()

    agent_log = AgentLog(Config=Config)

    parent_process = ParentProcess(config, agent_log)
    signal.signal(signal.SIGINT, parent_process.signal_handler)
    signal.signal(signal.SIGTERM, parent_process.signal_handler)

    check_store = CheckResultStore()

    webserver = Webserver(config, agent_log, check_store)
    webserver.start_webserver()

    # Start the web server in a new thread
    webserver_thread = threading.Thread(target=webserver.httpd.serve_forever)
    webserver_thread.start()

    check_params = {
        "timeout": 5
    }

    checks = [
        DefaultChecks(config, agent_log, check_store, check_params),
        SystemdChecks(config, agent_log, check_store, check_params)
    ]

    check_interval = config.config.getint('default', 'interval', fallback=5)
    if (check_interval <= 0):
        agent_log.info('check_interval <= 0. Using 5 seconds as check_interval for now.')
        check_interval = 5

    # Run checks on agent startup
    check_interval_counter = check_interval
    while parent_process.loop is True:
        print(parent_process.loop)
        if (check_interval_counter >= check_interval):
            # Execute checks
            print('run checks')
            check_interval_counter = 1
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                i = 0
                for check in checks:
                    print('Starting new Thread %d', i)
                    i += 1
                    executor.submit(check.real_check_run)
        else:
            print('Sleep wait for next run ', check_interval_counter, '/', check_interval)
            check_interval_counter += 1
            time.sleep(1)

    agent_log.info("Agent is going to shut down")

    # Also kill the webserver
    webserver.httpd.shutdown()
    webserver_thread.join()
    agent_log.info("Web server stopped")

    agent_log.info("Agent stopped")

