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

# supports python >= 3.7
#
# current psutil>=5.5.0,<=5.6.2 limitation due to https://github.com/giampaolo/psutil/issues/1723
import concurrent.futures
import signal
import time

from src.checks.default_checks import DefaultChecks
from src.checks.systemd_checks import SystemdChecks
from src.parent_process import ParentProcess
from src.config import Config
from src.agent_log import AgentLog
from src.check_result_store import CheckResultStore

if __name__ == '__main__':

    agentVersion = "2.0.0"

    config = Config(agentVersion)
    config.load_configuration()

    agent_log = AgentLog(Config=Config)

    check_store = CheckResultStore()
    check_params = {
        "timeout": 5
    }

    checks = [DefaultChecks(config, agent_log, check_store, check_params),
              SystemdChecks(config, agent_log, check_store, check_params)]

    #    default_checks = default_checks(config, agent_log, check_store, check_params)
    #    default_checks.real_check_run()

    # i = 0
    # for check in checks:
    #    print('Starting new Thread', i)
    #    i += 1
    #    check.real_check_run()

    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            i = 0
            for check in checks:
                print('Starting new Thread %d', i)
                i += 1
                executor.submit(check.real_check_run)

    print('all done')

    result = check_store.get_store()

    print(str(result))

    # logging.info("Testing update. Ending value is %d.", database.value)

# ParentProcess = ParentProcess()

# signal.signal(signal.SIGINT, ParentProcess.signal_handler)
# signal.signal(signal.SIGTERM, ParentProcess.signal_handler)

# ParentProcess.load_main_processing()

# try:
#    while True:
#        signal.pause()
# except AttributeError:
#    # signal.pause() is missing for Windows; wait 1ms and loop instead
#    while True:
#        time.sleep(0.1)
