from src.config import Config
from src.agent_log import AgentLog


class ParentProcess:
    Config = None  # type: Config
    agent_log = None  # type: AgentLog

    def __init__(self, Config, AgentLog):
        self.Config = Config
        self.agent_log = AgentLog

    def load_main_processing(self):
        """(Entry point) Function that initializes or reinitializes the agent on each call


        Starts ...

            - openITCOCKPIT Notification Thread (if enabled)
            - customchecks collector thread (if needed)
            - default check thread (including daily certificate expiration check)
            - webserver thread

        ... after (running check thread are stopped,) configuration is loaded and automatic certificate check is done.

        """
        global initialized

        while not reload_all():
            sleep(1)

        if autossl:
            check_auto_certificate()  # need to be called before initialized = True to prevent webserver thread restart

        initialized = True

        agent_log.info('Push mode enabled: %s', config['oitc']['enabled'])

        if 'oitc' in config and (
                config['oitc']['enabled'] in (1, "1", "true", "True", True) or added_oitc_parameter == 4):
            oitc_notification_thread(notify_oitc, (config['oitc'],))

        if config['default']['customchecks'] != "":
            if file_readable(config['default']['customchecks']):
                with open(config['default']['customchecks'], 'r') as customchecks_configfile:
                    print_verbose('Load custom check configuration file "%s"' % (config['default']['customchecks']),
                                  False)
                    agent_log.info('Load custom check configuration file "%s"' % (config['default']['customchecks']))
                    customchecks.read_file(customchecks_configfile)
                if customchecks:
                    permanent_customchecks_check_thread(collect_customchecks_data_for_cache, (customchecks,))

        permanent_check_thread(collect_data_for_cache, (int(config['default']['interval']),))
        permanent_webserver_thread(process_webserver, (enableSSL,))

    def signal_handler(sig, frame):
        """A custom signal handler to stop the agent if it is called"""
        global thread_stop_requested
        global webserver_stop_requested
        global wait_and_check_auto_certificate_thread_stop_requested

        thread_stop_requested = True
        webserver_stop_requested = True
        wait_and_check_auto_certificate_thread_stop_requested = True
        agent_log.info("Agent stopped")

        if self.Config.verbose:
            print("Agent stopped\n")
        sys.exit(0)
