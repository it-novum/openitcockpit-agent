pipeline {
    agent any
    
    stages {
        stage('Build agent linux packages') {
            when {
                beforeAgent true
                branch 'dronetest'
            }
            agent {
                docker { 
                    image 'srvitsmdrone01.master.dns:5000/openitcockpit-agent-centos7:latest'
                    registryUrl 'http://srvitsmdrone01.master.dns:5000'
                }
            }
            steps {
                sh 'yum -y install python36-devel python36-pip libffi-devel gcc glibc ruby-devel make rpm-build rubygems rpm'
                sh 'gem install --no-ri --no-rdoc fpm'
                sh 'mkdir -p ./public/{packages,binaries}'
                
                sh 'pip3 install -r requirements.txt'
                sh 'pyinstaller oitc_agent.py --onefile'
                
                sh 'mv ./dist/oitc_agent ./public/binaries/openitcockpit-agent-python3.linux.bin'
                sh 'chmod +x ./public/binaries/openitcockpit-agent-python3.linux.bin'
                sh '/bin/cp -f ./public/binaries/openitcockpit-agent-python3.linux.bin executables'
                sh './packages/scripts/build_linux_ci.sh'
                sh 'mv openitcockpit-agent*.{deb,rpm} ./public/packages'
                archiveArtifacts artifacts: 'public/packages/**', fingerprint: true
            }
        }
        stage('Nothing done') {
            when {
                beforeAgent true
                not {
                    branch 'master'
                }
            }
            steps {
                echo 'Nothing done'
            }
        }
    }
}
 
