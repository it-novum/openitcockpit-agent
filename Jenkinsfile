pipeline {
    agent any
    
    stages {
        stage('Build agent linux packages') {
            when {
                beforeAgent true
                anyOf{
                    //changeRequest target: 'master'
                    //branch 'master'
                    //changeRequest target: 'development'
                    //branch 'development'
                    changeRequest target: '2.0_build'
                    branch '2.0_build'
                }
            }
            agent {
                docker { 
                    image 'srvitsmdrone01.master.dns:5000/openitcockpit-agent-centos7-python39:latest'
                    registryUrl 'http://srvitsmdrone01.master.dns:5000'
                    args '-u root --privileged'
                }
            }
            steps {
                sh 'yum -y install libffi-devel gcc glibc ruby-devel make rpm-build rubygems rpm bsdtar'
                sh '/bin/bash -c "source /etc/profile.d/rvm.sh && rvm use 2.7 --default && gem install --no-document fpm"'
                sh 'mkdir -p ./public/{packages,binaries}'
                sh 'mkdir -p ./release'

                sh 'LD_LIBRARY_PATH=/usr/local/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}} pip3.9 install -r requirements.txt'
                dir ('src') {
                    sh 'LD_LIBRARY_PATH=/usr/local/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}} pyinstaller agent_nix.py --distpath "../dist" -n openitcockpit-agent-python3 --onefile'
                }

                
                sh 'mv ./dist/openitcockpit-agent-python3 ./public/binaries/openitcockpit-agent-python3.linux.bin'
                sh 'chmod +x ./public/binaries/openitcockpit-agent-python3.linux.bin'
                sh '/bin/cp -f ./public/binaries/openitcockpit-agent-python3.linux.bin executables'
                sh '/bin/bash -c "source /etc/profile.d/rvm.sh && rvm use 2.7 --default && ./packages/scripts/build_linux_ci.sh"'
                sh 'mv openitcockpit-agent*.{deb,rpm,pkg.tar.xz} ./release'
                sh 'chown 111:116 . -R'
                archiveArtifacts artifacts: 'release/**', fingerprint: true
                script {
                    stash includes: 'release/**', name: 'release'
                }
            }
        }
        //stage('Publish linux packages - Stable 2.0') {
        //    when {
        //        beforeAgent true
        //        branch 'master'
        //    }
        //    environment {
        //        VERSION = """${sh(
        //            returnStdout: true,
        //            script: 'cat version | xargs | tr -d \'\n\''
        //        )}"""
        //    }
        //    steps {
        //        script {
        //            unstash 'release'
        //        }
        //        sh 'mkdir -p /tmp/agent/test; rm -r /tmp/agent/*'
        //        sh 'rsync -avz --progress release/* /tmp/agent'
        //        sh '/var/lib/jenkins/openITCOCKPIT-build/aptly.sh repo add -force-replace buster-agent-stable /tmp/agent/openitcockpit-agent_*amd64.deb; /var/lib/jenkins/openITCOCKPIT-build/aptly.sh repo add -force-replace focal-agent-stable /tmp/agent/openitcockpit-agent_*amd64.deb; /var/lib/jenkins/openITCOCKPIT-build/aptly.sh repo add -force-replace bionic-agent-stable /tmp/agent/openitcockpit-agent_*amd64.deb'
        //        sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa oitc@172.16.101.32 "mkdir -p /var/www/openitcockpit_io/files/openitcockpit-agent"'
        //        sh 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa" --delete --progress release/* oitc@172.16.101.32:/var/www/openitcockpit_io/files/openitcockpit-agent'
        //    }
        //}
        stage('Publish linux packages - Nightly 2.0') {
            when {
                beforeAgent true
                branch '2.0_build'
            }
            environment {
                VERSION = """${sh(
                    returnStdout: true,
                    script: 'cat version | xargs | tr -d \'\n\''
                )}"""
            }
            steps {
                script {
                    unstash 'release'
                }
                sh 'mkdir -p /tmp/agent/test; rm -r /tmp/agent/*'
                sh 'rsync -avz --progress release/* /tmp/agent'
                sh '/var/lib/jenkins/openITCOCKPIT-build/aptly.sh repo add -force-replace buster-agent-nightly /tmp/agent/openitcockpit-agent_*amd64.deb; /var/lib/jenkins/openITCOCKPIT-build/aptly.sh repo add -force-replace focal-agent-nightly /tmp/agent/openitcockpit-agent_*amd64.deb; /var/lib/jenkins/openITCOCKPIT-build/aptly.sh repo add -force-replace bionic-agent-nightly /tmp/agent/openitcockpit-agent_*amd64.deb'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa oitc@172.16.101.32 "mkdir -p /var/www/openitcockpit_io/files/openitcockpit-agent-nightly-2.0"'
                sh 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa" --progress release/* oitc@172.16.101.32:/var/www/openitcockpit_io/files/openitcockpit-agent-nightly-2.0'
            }
        }
        stage('Build agent windows packages') {
            when {
                beforeAgent true
                anyOf{
                    //changeRequest target: 'master'
                    //branch 'master'
                    //changeRequest target: 'development'
                    //branch 'development'
                    changeRequest target: '2.0_build'
                    branch '2.0_build'
                }
            }
            environment {
                VERSION = """${sh(
                    returnStdout: true,
                    script: 'cat version | xargs | tr -d \'\n\''
                )}"""
            }
            steps {
                sh """
                    sed -i -e 's|/etc/openitcockpit-agent/|C:\\\\Program\\ Files\\\\it-novum\\\\openitcockpit-agent\\\\|g' example_config.cnf
                   """
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa kress@172.16.166.223 if exist openitcockpit-agent-2.0 rmdir /Q /S openitcockpit-agent-2.0'
                sh 'scp -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa -r ./ kress@172.16.166.223:openitcockpit-agent-2.0'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa kress@172.16.166.223 powershell "cd openitcockpit-agent-2.0; python.exe -m venv ./python3-windows-env; ./python3-windows-env/Scripts/activate.bat; ./python3-windows-env/Scripts/pip.exe install -r requirements.txt pywin32; cd src; ../python3-windows-env/Scripts/pyinstaller.exe agent_windows.py --distpath ../dist --onefile -n openitcockpit-agent-python3; cd ..; ./python3-windows-env/Scripts/deactivate.bat"'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa kress@172.16.166.223 powershell "cd openitcockpit-agent-2.0; mv ./dist/openitcockpit-agent-python3.exe executables/openitcockpit-agent-python3.exe; rm -r -fo ./dist; rm -r -fo ./build; rm -r -fo ./__pycache__; rm -r -fo ./openitcockpit-agent-python3.spec; rm -r -fo ./python3-windows-env"'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa kress@172.16.166.223 powershell "openitcockpit-agent-2.0/packages/scripts/build_msi.bat"'
                sh 'mkdir -p ./release'
                sh 'scp -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa kress@172.16.166.223:openitcockpit-agent-2.0/executables/openitcockpit-agent-${VERSION}-amd64.msi ./release'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa kress@172.16.166.223 powershell "rm -r -fo openitcockpit-agent-2.0"'
                archiveArtifacts artifacts: 'release/**', fingerprint: true
                script {
                    stash includes: 'release/**', name: 'windowsrelease'
                }
            }
        }
        //stage('Publish windows package - Stable 2.0') {
        //    when {
        //        beforeAgent true
        //        branch 'master'
        //    }
        //    environment {
        //        VERSION = """${sh(
        //            returnStdout: true,
        //            script: 'cat version | xargs | tr -d \'\n\''
        //        )}"""
        //    }
        //    steps {
        //        script {
        //            unstash 'windowsrelease'
        //        }
        //        sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa oitc@172.16.101.32 "mkdir -p /var/www/openitcockpit_io/files/openitcockpit-agent"'
        //        sh 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa" --progress release/* oitc@172.16.101.32:/var/www/openitcockpit_io/files/openitcockpit-agent'
        //    }
        //}
        stage('Publish windows package - Nightly 2.0') {
            when {
                beforeAgent true
                branch '2.0_build'
            }
            environment {
                VERSION = """${sh(
                    returnStdout: true,
                    script: 'cat version | xargs | tr -d \'\n\''
                )}"""
            }
            steps {
                script {
                    unstash 'windowsrelease'
                }
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa oitc@172.16.101.32 "mkdir -p /var/www/openitcockpit_io/files/openitcockpit-agent-nightly-2.0"'
                sh 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa" --progress release/* oitc@172.16.101.32:/var/www/openitcockpit_io/files/openitcockpit-agent-nightly-2.0'
            }
        }
        stage('Build agent macOS packages') {
            when {
                beforeAgent true
                anyOf{
                    //changeRequest target: 'master'
                    //branch 'master'
                    //changeRequest target: 'development'
                    //branch 'development'
                    changeRequest target: '2.0_build'
                    branch '2.0_build'
                }
            }
            environment {
                VERSION = """${sh(
                    returnStdout: true,
                    script: 'cat version | xargs | tr -d \'\n\''
                )}"""
            }
            steps {
                sh """
                    sed -i -e 's|C:\\\\Program\\ Files\\\\it-novum\\\\openitcockpit-agent\\\\|/Applications/openitcockpit-agent/|g' example_config.cnf
                   """

                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn "rm -rf openitcockpit-agent-packages-2.0"'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn "mkdir -p openitcockpit-agent-packages-2.0/openitcockpit-agent"'
                sh 'scp -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa -r ./ admin@itsm-mojave.oitc.itn:openitcockpit-agent-packages-2.0/openitcockpit-agent'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn "cd openitcockpit-agent-packages-2.0/openitcockpit-agent; /usr/local/bin/python3 -m venv ./python3-macos-env; source ./python3-macos-env/bin/activate; rm ./python3-macos-env/bin/python3; cp /usr/local/bin/python3 ./python3-macos-env/bin; ./python3-macos-env/bin/python3 -m pip install -r requirements.txt pyinstaller; cd src; ../python3-macos-env/bin/python3 ../python3-macos-env/bin/pyinstaller agent_nix.py --distpath ../dist -n openitcockpit-agent-python3 --onefile; cd ..; deactivate"'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn "cd openitcockpit-agent-packages-2.0/openitcockpit-agent; mv ./dist/openitcockpit-agent-python3 ./executables/openitcockpit-agent-python3.macos.bin; chmod +x ./executables/openitcockpit-agent-python3.macos.bin; rm -r ./python3-macos-env ./dist ./build ./__pycache__ openitcockpit-agent-python3.spec; cd ..; ./openitcockpit-agent/packages/scripts/build_macos.sh; rm -r package_osx package_osx_uninstaller"'
                sh 'mkdir -p ./release'
                sh 'scp -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn:openitcockpit-agent-packages-2.0/openitcockpit-agent-${VERSION}-darwin-amd64.pkg ./release'
                sh 'scp -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn:openitcockpit-agent-packages-2.0/openitcockpit-agent-uninstaller-${VERSION}-darwin-amd64.pkg ./release'
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa admin@itsm-mojave.oitc.itn "rm -rf openitcockpit-agent-packages-2.0"'
                archiveArtifacts artifacts: 'release/**', fingerprint: true
                script {
                    stash includes: 'release/**', name: 'macosrelease'
                }
            }
        }
        //stage('Publish macOS package - Stable 2.0') {
        //    when {
        //        beforeAgent true
        //        branch 'master'
        //    }
        //    environment {
        //        VERSION = """${sh(
        //            returnStdout: true,
        //            script: 'cat version | xargs | tr -d \'\n\''
        //        )}"""
        //    }
        //    steps {
        //        script {
        //            unstash 'macosrelease'
        //        }
        //        sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa oitc@172.16.101.32 "mkdir -p /var/www/openitcockpit_io/files/openitcockpit-agent"'
        //        sh 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa" --progress release/* oitc@172.16.101.32:/var/www/openitcockpit_io/files/openitcockpit-agent'
        //    }
        //}
        stage('Publish macOS package - Nightly 2.0') {
            when {
                beforeAgent true
                branch '2.0_build'
            }
            environment {
                VERSION = """${sh(
                    returnStdout: true,
                    script: 'cat version | xargs | tr -d \'\n\''
                )}"""
            }
            steps {
                script {
                    unstash 'macosrelease'
                }
                sh 'ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa oitc@172.16.101.32 "mkdir -p /var/www/openitcockpit_io/files/openitcockpit-agent-nightly-2.0"'
                sh 'rsync -avz -e "ssh -o StrictHostKeyChecking=no -i /var/lib/jenkins/.ssh/id_rsa" --progress release/* oitc@172.16.101.32:/var/www/openitcockpit_io/files/openitcockpit-agent-nightly-2.0'
            }
        }
        stage('Nothing done') {
            when {
                beforeAgent true
                not {
                    branch 'master'
                }
                not {
                    changeRequest target: 'master'
                }
                not {
                    branch 'development'
                }
                not {
                    changeRequest target: 'development'
                }
                not {
                    branch '2.0_build'
                }
                not {
                    changeRequest target: '2.0_build'
                }
            }
            steps {
                echo 'Nothing done'
            }
        }
    }
}
 
