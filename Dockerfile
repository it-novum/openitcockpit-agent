FROM centos:centos7

RUN yum -y update
RUN yum -y install python36-devel python36-pip libffi-devel gcc glibc which curl
RUN yum -y install ruby-devel gcc make rpm-build rubygems rpm
RUN curl -sSL https://rvm.io/mpapis.asc | gpg2 --import -
RUN curl -sSL https://rvm.io/pkuczynski.asc | gpg2 --import -
RUN curl -L get.rvm.io | bash -s stable
RUN /bin/bash -c "source /etc/profile.d/rvm.sh && rvm reload && rvm requirements run && rvm install 2.7 && rvm use 2.7 --default"

ENTRYPOINT /bin/bash
