cd openitcockpit-agent
set /p version=<version
"C:\Program Files (x86)\Caphyon\Advanced Installer 17.6\bin\x86\advinst.exe" /edit "C:\Users\kress\openitcockpit-agent-2.0\msi\openitcockpit-agent.aip" \SetVersion "%version%"
"C:\Program Files (x86)\Caphyon\Advanced Installer 17.6\bin\x86\advinst.exe" /build "C:\Users\kress\openitcockpit-agent-2.0\msi\openitcockpit-agent.aip"
