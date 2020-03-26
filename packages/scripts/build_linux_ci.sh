#!/bin/bash

version=`cat version | xargs`

mkdir -p package/usr/bin
mkdir -p package/etc/openitcockpit-agent/

cp executables/openitcockpit-agent-python3.linux.bin package/usr/bin/
cp example_config.cnf package/etc/openitcockpit-agent/config.cnf
cp example_customchecks.cnf package/etc/openitcockpit-agent/customchecks.cnf
cp -r packages/init package/etc/openitcockpit-agent/

# Debian / Ubuntu x64
fpm -s dir -t deb -C package --name openitcockpit-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files etc/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install packages/preinst.sh --after-install packages/postinst.sh --before-remove packages/prerm.sh --version "$version"

# RedHat / CentOS x64
fpm -s dir -t rpm -C package --name openitcockpit-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files etc/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install packages/preinst.sh --after-install packages/postinst.sh --before-remove packages/prerm.sh --version "$version"

# Arch (pacman)
fpm -s dir -t pacman -C package --name openitcockpit-agent --vendor "it-novum GmbH" --license "Apache License Version 2.0" --config-files etc/openitcockpit-agent --architecture native --maintainer "<daniel.ziegler@it-novum.com>" --description "openITCOCKPIT Monitoring Agent and remote plugin executor." --url "https://openitcockpit.io" --before-install packages/preinst.sh --after-install packages/postinst.sh --before-remove packages/prerm.sh --version "$version"
