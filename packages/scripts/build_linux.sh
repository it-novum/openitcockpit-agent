#!/bin/bash

if [ -d "$(pwd)/openitcockpit-agent" ]; then
    cd openitcockpit-agent/
    git pull
    cd ../
else
    git clone --depth=1 https://github.com/it-novum/openitcockpit-agent.git
fi


mkdir -p package/usr/bin
mkdir -p package/etc/openitcockpit-agent/

cp openitcockpit-agent/executables/openitcockpit-agent-python3.linux.bin package/usr/bin/
cp openitcockpit-agent/example_config.cnf package/etc/openitcockpit-agent/config.cnf
cp openitcockpit-agent/example_customchecks.cnf package/etc/openitcockpit-agent/customchecks.cnf
cp -r openitcockpit-agent/packages/init package/etc/openitcockpit-agent/

# Debian / Ubuntu x64
fpm -s dir -t deb -C package --name openitcockpit-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files etc/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install openitcockpit-agent/packages/preinst.sh --after-install openitcockpit-agent/packages/postinst.sh --before-remove openitcockpit-agent/packages/prerm.sh --version "1.0.0"

# RedHat / CentOS x64
fpm -s dir -t rpm -C package --name openitcockpit-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files etc/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install openitcockpit-agent/packages/preinst.sh --after-install openitcockpit-agent/packages/postinst.sh --before-remove openitcockpit-agent/packages/prerm.sh --version "1.0.0"

