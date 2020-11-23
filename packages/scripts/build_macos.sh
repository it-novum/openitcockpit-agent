#!/bin/bash
#
#
# This script can ONLY be executed on a macOS system!
#

if [ -d "$(pwd)/openitcockpit-agent" ]; then
    cd openitcockpit-agent/
    git pull
    cd ../
else
    git clone --depth=1 https://github.com/it-novum/openitcockpit-agent.git
fi


version=`cat openitcockpit-agent/version | xargs`

mkdir -p package_osx/Applications/openitcockpit-agent

cp openitcockpit-agent/executables/openitcockpit-agent-python3.macos.bin package_osx/Applications/openitcockpit-agent/
cp openitcockpit-agent/example_config.cnf package_osx/Applications/openitcockpit-agent/config.cnf
cp openitcockpit-agent/example_customchecks.cnf package_osx/Applications/openitcockpit-agent/customchecks.cnf
cp openitcockpit-agent/packages/init/com.it-novum.openitcockpit.agent.plist package_osx/Applications/openitcockpit-agent/com.it-novum.openitcockpit.agent.plist

# MacOS x64 Installer (only runs on macOS)
/usr/local/lib/ruby/gems/2.7.0/bin/fpm -s dir -t osxpkg -C package_osx --name openitcockpit-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files Applications/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install openitcockpit-agent/packages/preinst.sh --after-install openitcockpit-agent/packages/postinst.sh --version "$version"
mv openitcockpit-agent-${version}.pkg openitcockpit-agent-${version}-darwin-amd64.pkg

mkdir -p package_osx_uninstaller

# MacOS x64 Uninstaller (only runs on macOS)
/usr/local/lib/ruby/gems/2.7.0/bin/fpm -s dir -t osxpkg -C package_osx_uninstaller --name openitcockpit-agent-uninstaller --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files Applications/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install openitcockpit-agent/packages/prerm.sh --version "$version" --osxpkg-payload-free
mv openitcockpit-agent-uninstaller-${version}.pkg openitcockpit-agent-uninstaller-${version}-darwin-amd64.pkg
