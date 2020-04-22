cd openitcockpit-agent
set /p version=<version
cd msi
"C:/Program Files (x86)/WiX Toolset v3.11/bin/candle.exe" -v -arch x64 Product.wxs WixUi_Main.wxs LicenseAgreementDlg_HK.wxs SetConfigurationUnInstallDlg_HK.wxs -dVersionNumber="%version%" -ext WixNetFxExtension -ext WixFirewallExtension -ext WixUtilExtension
"C:/Program Files (x86)/WiX Toolset v3.11/bin/light.exe" Product.wixobj WixUi_Main.wixobj LicenseAgreementDlg_HK.wixobj SetConfigurationUnInstallDlg_HK.wixobj -o openitcockpit-agent.msi -loc Product_en-us.wxl -ext WixUIExtension -ext WixNetFxExtension -ext WixFirewallExtension -ext WixUtilExtension -sw1076
