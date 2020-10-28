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
import signal
import time

from src.Checks.DefaultChecks import DefaultChecks
from src.ParentProcess import ParentProcess
from src.Config import Config
from src.AgentLog import AgentLog
from src.CheckResultStore import CheckResultStore

if __name__ == '__main__':

    agentVersion = "2.0.0"

    config = Config(agentVersion)
    config.load_configuration()

    agent_log = AgentLog(Config=Config)

    check_store = CheckResultStore()
    check_params = {}


    default_checks = DefaultChecks(config, agent_log, check_store, check_params)
    default_checks.real_check_run()



   #ParentProcess = ParentProcess()

   #signal.signal(signal.SIGINT, ParentProcess.signal_handler)
   #signal.signal(signal.SIGTERM, ParentProcess.signal_handler)

   #ParentProcess.load_main_processing()

   #try:
   #    while True:
   #        signal.pause()
   #except AttributeError:
   #    # signal.pause() is missing for Windows; wait 1ms and loop instead
   #    while True:
   #        time.sleep(0.1)
