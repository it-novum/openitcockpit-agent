cd openitcockpit-agent/msi
"C:/Program Files (x86)/WiX Toolset v3.11/bin/candle.exe" -v -arch x64 Product.wxs WixUi_Main.wxs LicenseAgreementDlg_HK.wxs -dVersionNumber="1.0.0"
"C:/Program Files (x86)/WiX Toolset v3.11/bin/light.exe" Product.wixobj WixUi_Main.wixobj LicenseAgreementDlg_HK.wixobj -o openitcockpit-agent.msi -loc Product_en-us.wxl -ext WixUIExtension -sw1076
