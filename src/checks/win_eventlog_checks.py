import sys
import traceback

from checks.default_check import DefaultCheck

if sys.platform == 'win32' or sys.platform == 'win64':
    import win32evtlog
    import win32evtlogutil
    import win32con
    import win32security  # To translate NT Sids to account names.

from utils.operating_system import OperatingSystem


class WinEventlogChecks(DefaultCheck):

    def __init__(self, config, agent_log, check_store, check_params):
        super().__init__(config, agent_log, check_store, check_params)
        self.key_name = "windows_eventlog"

    def run_check(self) -> dict:
        self.agent_log.verbose('Running Windows event log checks')

        windows_eventlog = {}
        try:
            server = 'localhost'  # name of the target computer to get event logs
            logTypes = []
            fallback_logtypes = 'System, Application, Security'
            if self.Config.config.get('default', 'wineventlog-logtypes', fallback=fallback_logtypes) != "":
                for logtype in self.Config.config.get('default', 'wineventlog-logtypes',
                                                      fallback=fallback_logtypes).split(','):
                    if logtype.strip() != '':
                        logTypes.append(logtype.strip())
            else:
                logTypes = ['System', 'Application', 'Security']

            evt_dict = {
                win32con.EVENTLOG_AUDIT_FAILURE: 'EVENTLOG_AUDIT_FAILURE',  # 16 -> critical
                win32con.EVENTLOG_AUDIT_SUCCESS: 'EVENTLOG_AUDIT_SUCCESS',  # 8  -> ok
                win32con.EVENTLOG_INFORMATION_TYPE: 'EVENTLOG_INFORMATION_TYPE',  # 4  -> ok
                win32con.EVENTLOG_WARNING_TYPE: 'EVENTLOG_WARNING_TYPE',  # 2  -> warning
                win32con.EVENTLOG_ERROR_TYPE: 'EVENTLOG_ERROR_TYPE'  # 1  -> critical
            }

            for logType in logTypes:
                try:
                    if logType not in windows_eventlog:
                        windows_eventlog[logType] = []
                    hand = win32evtlog.OpenEventLog(server, logType)
                    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                    total = win32evtlog.GetNumberOfEventLogRecords(hand)
                    events = win32evtlog.ReadEventLog(hand, flags, 0)
                    if events:
                        for event in events:
                            msg = win32evtlogutil.SafeFormatMessage(event, logType)
                            sidDesc = None
                            if event.Sid is not None:
                                try:
                                    domain, user, typ = win32security.LookupAccountSid(server, event.Sid)
                                    sidDesc = "%s/%s" % (domain, user)
                                except win32security.error:
                                    sidDesc = str(event.Sid)

                            evt_type = "unknown"
                            if event.EventType in evt_dict.keys():
                                evt_type = str(evt_dict[event.EventType])

                            tmp_evt = {
                                'event_category': event.EventCategory,
                                'time_generated': str(event.TimeGenerated),
                                'source_name': event.SourceName,
                                'associated_user': sidDesc,
                                'event_id': event.EventID,
                                'event_type': evt_type,
                                'event_type_id': event.EventType,
                                'event_msg': msg,
                                'event_data': [data for data in
                                               event.StringInserts] if event.StringInserts else ''
                            }
                            windows_eventlog[logType].append(tmp_evt)

                except Exception as e:
                    self.agent_log.error(
                        "An error occurred during windows eventlog check with log type %s!" % (logType))
                    self.agent_log.error(str(e))
                    self.agent_log.stacktrace(traceback.format_exc())

        except:
            self.agent_log.error("An error occurred during windows eventlog check!")
            self.agent_log.stacktrace(traceback.format_exc())

        return windows_eventlog.copy()
