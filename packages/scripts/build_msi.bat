cd openitcockpit-agent
set /p version=<version
cd msi
"C:/Program Files (x86)/WiX Toolset v3.11/bin/candle.exe" -v -arch x64 Product.wxs WixUi_Main.wxs LicenseAgreementDlg_HK.wxs -dVersionNumber="%version%" -ext WixNetFxExtension
"C:/Program Files (x86)/WiX Toolset v3.11/bin/light.exe" Product.wixobj WixUi_Main.wixobj LicenseAgreementDlg_HK.wixobj -o openitcockpit-agent.msi -loc Product_en-us.wxl -ext WixUIExtension -ext WixNetFxExtension -sw1076
