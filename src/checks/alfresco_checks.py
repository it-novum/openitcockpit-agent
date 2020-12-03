import subprocess
import traceback

from checks.Check import Check
from filesystem import Filesystem
from operating_system import OperatingSystem


class AlfrescoChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.key_name = "alfresco_checks"

        self.alfresco_stats_data = {}

        self.jmx_import_successfull = False
        try:
            from jmxquery import JMXConnection, JMXQuery, JMXConnection
            self.jmx_import_successfull = True
        except:
            print('jmxquery not found!')
            self.agent_log.error('jmxquery not found!')
            print('If you want to use the alfresco stats check try: pip3 install jmxquery')
            self.agent_log.error('If you want to use the alfresco stats check try: pip3 install jmxquery')

    def run_check(self) -> dict:
        """Function that starts as a thread to run the alfresco stats check

        Function that a jmx query to get a status result for a configured alfresco enterprise instance.

        """
        if self.Config.verbose:
            self.agent_log.verbose('Start alfresco stats check')

        self.alfresco_stats_data['running'] = "true"

        alfrescostats = []

        if self.jmx_import_successfull and self.Config.config.getboolean('default', 'alfrescostats', fallback=False):
            if Filesystem.file_readable(self.Config.config['default']['alfresco-javapath']):
                try:
                    uri = ("%s:%s%s" % (
                        self.Config.config['default']['alfresco-jmxaddress'],
                        self.Config.config['default']['alfresco-jmxport'],
                        self.Config.config['default']['alfresco-jmxpath']))
                    alfresco_jmxConnection = JMXConnection("service:jmx:rmi:///jndi/rmi://" + uri,
                                                           self.Config.config['default']['alfresco-jmxuser'],
                                                           self.Config.config['default']['alfresco-jmxpassword'],
                                                           self.Config.config['default']['alfresco-javapath'])
                    alfresco_jmxQueryString = "java.lang:type=Memory/HeapMemoryUsage/used;java.lang:type=OperatingSystem/SystemLoadAverage;java.lang:type=Threading/ThreadCount;Alfresco:Name=Runtime/TotalMemory;Alfresco:Name=Runtime/FreeMemory;Alfresco:Name=Runtime/MaxMemory;Alfresco:Name=WorkflowInformation/NumberOfActivitiWorkflowInstances;Alfresco:Name=WorkflowInformation/NumberOfActivitiTaskInstances;Alfresco:Name=Authority/NumberOfGroups;Alfresco:Name=Authority/NumberOfUsers;Alfresco:Name=RepoServerMgmt/UserCountNonExpired;Alfresco:Name=ConnectionPool/NumActive;Alfresco:Name=License/RemainingDays;Alfresco:Name=License/CurrentUsers;Alfresco:Name=License/MaxUsers"

                    if 'alfresco-jmxquery' in self.Config.config and self.Config.config['default'][
                        'alfresco-jmxquery'] != "":
                        print("customquerx")
                        self.agent_log.info("customquerx")
                        alfresco_jmxQueryString = self.Config.config['default']['alfresco-jmxquery']

                    alfresco_jmxQuery = [JMXQuery(alfresco_jmxQueryString)]
                    alfresco_metrics = alfresco_jmxConnection.query(alfresco_jmxQuery)

                    for metric in alfresco_metrics:
                        alfrescostats.append({
                            'name': metric.to_query_string(),
                            'value': str(metric.value),
                            'value_type': str(metric.value_type)
                        })

                except subprocess.CalledProcessError as e:
                    alfrescostats = "An error occurred during alfresco stats check while connecting to jmx!"
                    self.agent_log.error(alfrescostats)
                    self.agent_log.stacktrace(traceback.format_exc())

                except:
                    alfrescostats = "An error occurred during alfresco stats check!"
                    self.agent_log.error(alfrescostats)
                    self.agent_log.stacktrace(traceback.format_exc())

            else:
                alfrescostats = 'JAVA instance not found! (' + self.Config.config['default']['alfresco-javapath'] + ')'

        self.agent_log.verbose('Alfresco stats check finished')

        self.alfresco_stats_data['result'] = alfrescostats
        return self.alfresco_stats_data.copy()
