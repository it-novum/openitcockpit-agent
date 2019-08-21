using System;
using System.Diagnostics;
using System.ServiceProcess;
using System.Timers;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using System.Threading;

// MIT License

namespace OitcAgentSvc
{


    public partial class OitcAgentSvc : ServiceBase
    {

        public EventLog eventLog1;
        private int eventId = 1;

        public Process AgentProcess;

        // Using @ to not require escaping \
        private string registryKey = @"SOFTWARE\it-novum\InstalledProducts\oitcAgent\";
        private string agentPath = @"C:\Program Files\it-novum\oitcAgent\";


        public enum ServiceState
        {
            SERVICE_STOPPED = 0x00000001,
            SERVICE_START_PENDING = 0x00000002,
            SERVICE_STOP_PENDING = 0x00000003,
            SERVICE_RUNNING = 0x00000004,
            SERVICE_CONTINUE_PENDING = 0x00000005,
            SERVICE_PAUSE_PENDING = 0x00000006,
            SERVICE_PAUSED = 0x00000007,
        };

        [StructLayout(LayoutKind.Sequential)]
        public struct ServiceStatus
        {
            public int dwServiceType;
            public ServiceState dwCurrentState;
            public int dwControlsAccepted;
            public int dwWin32ExitCode;
            public int dwServiceSpecificExitCode;
            public int dwCheckPoint;
            public int dwWaitHint;
        };
        public OitcAgentSvc()
        {
            InitializeComponent();
            eventLog1 = new System.Diagnostics.EventLog();
            if (!System.Diagnostics.EventLog.SourceExists("oitcAgentSvc"))
            {
                System.Diagnostics.EventLog.CreateEventSource(
                    "oitcAgentSvc", "openITCOCKPIT Agent");
                Thread.Sleep(1000);
            }

            eventLog1 = new System.Diagnostics.EventLog();
            eventLog1.Source = "oitcAgentSvc";
            eventLog1.Log = "openITCOCKPIT Agent";
        }


        protected override void OnStart(string[] args)
        {
            eventLog1.WriteEntry("Starting openITCOCKPIT Monitoring Agent");
            // Set up a timer that triggers every minute.
            System.Timers.Timer timer = new System.Timers.Timer();
            timer.Interval = 60000; // 60 seconds
            timer.Elapsed += new ElapsedEventHandler(this.OnTimer);
            timer.Start();

            // Update the service state to Start Pending.
            ServiceStatus serviceStatus = new ServiceStatus();
            serviceStatus.dwCurrentState = ServiceState.SERVICE_START_PENDING;
            serviceStatus.dwWaitHint = 100000;
            SetServiceStatus(this.ServiceHandle, ref serviceStatus);

            RegistryKey regKey = Registry.LocalMachine.OpenSubKey(registryKey, false);
            if (regKey != null)
            {
                agentPath = (string)regKey.GetValue("InstallLocation");
            }

            string agentBin = agentPath + @"openitcockpit-agent-python3.exe";

            AgentProcess = new Process();

            AgentProcess.StartInfo.UseShellExecute = false;
            AgentProcess.StartInfo.FileName = agentBin;
            AgentProcess.StartInfo.CreateNoWindow = true;
            AgentProcess.Start();

            // Update the service state to Running.
            serviceStatus.dwCurrentState = ServiceState.SERVICE_RUNNING;
            SetServiceStatus(this.ServiceHandle, ref serviceStatus);
        }

        protected override void OnStop()
        {
            eventLog1.WriteEntry("Stopping openITCOCKPIT Monitoring Agent");
            //Workaround for pyinstaller issue: https://github.com/pyinstaller/pyinstaller/issues/2533
            foreach (Process process in Process.GetProcessesByName("openitcockpit-agent-python3"))
            {
                process.Kill();
            }
            //AgentProcess.Kill();
            AgentProcess.Close();
        }

        public void OnTimer(object sender, ElapsedEventArgs args)
        {
            // TODO: Insert monitoring activities here.
            eventLog1.WriteEntry("Monitoring the System", EventLogEntryType.Information, eventId++);
        }

        [DllImport("advapi32.dll", SetLastError = true)]
        private static extern bool SetServiceStatus(System.IntPtr handle, ref ServiceStatus serviceStatus);
    }
}