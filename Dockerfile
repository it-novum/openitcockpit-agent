FROM centos:centos7

RUN yum -y update \
&& yum -y install python36-devel python36-pip libffi-devel gcc glibc \
&& yum -y install ruby-devel gcc make rpm-build rubygems rpm

ENTRYPOINT /bin/bash
