import time
import traceback
import subprocess

from src.Checks.Check import Check
from src.OperatingSystem import OperatingSystem
from src.Filesystem import Filesystem


class ClfrescoChecks(Check):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.operating_system = OperatingSystem()

        self.alfresco_stats_data = {}
        self.cached_check_data = {}

        self.jmx_import_successfull = False
        try:
            from jmxquery import JMXConnection, JMXQuery, JMXConnection
            self.jmx_import_successfull = True
        except:
            print('jmxquery not found!')
            self.agent_log.error('jmxquery not found!')
            print('If you want to use the alfresco stats check try: pip3 install jmxquery')
            self.agent_log.error('If you want to use the alfresco stats check try: pip3 install jmxquery')

    def check_alfresco_stats(self):
        """Function that starts as a thread to run the alfresco stats check

        Function that a jmx query to get a status result for a configured alfresco enterprise instance.

        """
        global alfresco_stats_data
        global cached_check_data

        self.agent_log.info('Start alfresco stats check at %s' % (str(round(time.time()))))
        if self.Config.verbose:
            print('Start alfresco stats check at %s' % (str(round(time.time()))))

        alfresco_stats_data['running'] = "true"

        alfrescostats = []

        # todo refactor with: self.Config.config.getboolean('default', 'cpustats') is True
        # https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.getboolean
        # https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.BOOLEAN_STATES
        if self.jmx_import_successfull and 'alfrescostats' in self.Config.config['default'] and \
                self.Config.config['default'][
                    'alfrescostats'] in (
                1, "1", "true", "True", True):
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
                    alfrescostats = "An error occured during alfresco stats check while connecting to jmx!"
                    self.agent_log.error(alfrescostats)

                    if self.Config.stacktrace:
                        traceback.print_exc()

                except:
                    alfrescostats = "An error occured during alfresco stats check!"
                    self.agent_log.error(alfrescostats)

                    if self.Config.stacktrace:
                        traceback.print_exc()

            else:
                alfrescostats = 'JAVA instance not found! (' + self.Config.config['default']['alfresco-javapath'] + ')'

        alfresco_stats_data['result'] = alfrescostats
        cached_check_data['alfrescostats'] = alfrescostats
        self.agent_log.info('Alfresco stats check finished')
        del alfresco_stats_data['running']
