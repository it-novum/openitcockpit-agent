
## Build MSI on Windows

### Reqirements
Download and install [WiX gt 3.x](https://wixtoolset.org/)

Start CMD as Administrator

cd `msi` folder

````
"C:\Program Files (x86)\WiX Toolset v3.11\bin\candle.exe" -v -arch x64 Product.wxs
````


````
"C:\Program Files (x86)\WiX Toolset v3.11\bin\light.exe" Product.wixobj -o oitcAgent.msi -loc Product_en-us.wxl -ext WixUIExtension
````
