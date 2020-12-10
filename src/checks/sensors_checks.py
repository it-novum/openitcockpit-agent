import traceback

import psutil

from checks.default_check import DefaultCheck


class SensorsChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "sensors"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running sensor checks')

        sensors = {}
        try:
            if hasattr(psutil, "sensors_temperatures") and not self.operating_system.windows:
                sensors['temperatures'] = {}
                for device, data in psutil.sensors_temperatures(
                        fahrenheit=self.Config.temperatureIsFahrenheit).items():
                    sensors['temperatures'][device] = []
                    for value in data:
                        sensors['temperatures'][device].append(value._asdict())
            else:
                sensors['temperatures'] = {}
        except:
            self.agent_log.error("Could not get temperature sensor data!")
            self.agent_log.stacktrace(traceback.format_exc())

        try:
            if hasattr(psutil, "sensors_fans") and not self.operating_system.windows:
                sensors['fans'] = {}
                for device, data in psutil.sensors_fans().items():
                    sensors['fans'][device] = []
                    for value in data:
                        sensors['fans'][device].append(value._asdict())
            else:
                sensors['fans'] = {}
        except:
            self.agent_log.error("Could not get fans sensor data!")
            self.agent_log.stacktrace(traceback.format_exc())

        try:
            if hasattr(psutil, "sensors_battery"):
                sensors_battery = psutil.sensors_battery()
                if sensors_battery is not None:
                    sensors['battery'] = sensors_battery._asdict()
                else:
                    sensors['battery'] = {}
            else:
                sensors['battery'] = {}
        except:
            self.agent_log.error("Could not get battery sensor data!")
            self.agent_log.stacktrace(traceback.format_exc())

        return sensors.copy()
