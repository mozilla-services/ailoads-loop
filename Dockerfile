FROM stackbrew/debian:wheezy
MAINTAINER Mozilla Cloud Services

RUN echo "deb http://ftp.debian.org/debian sid main" >> /etc/apt/sources.list

RUN apt-get update
RUN apt-get install -y python3-pip
RUN apt-get install -y python-virtualenv
RUN apt-get install -y git
RUN apt-get install -y wget
RUN apt-get install -y python3-dev

# sshd
RUN apt-get -y install openssh-server
RUN mkdir /var/run/sshd
RUN sed -i "s/#PasswordAuthentication yes/PasswordAuthentication no/" /etc/ssh/sshd_config

# Adding loads user
RUN adduser --system loads
USER loads

# deploying the loads-broker project
RUN git clone https://github.com/tarekziade/ailoads-loop /home/loads/ailoads-loop
RUN cd /home/loads/ailoads-loop; make build

EXPOSE 22
EXPOSE 8080
EXPOSE 8083
EXPOSE 8086
EXPOSE 8084

ADD boto.cfg /etc/boto.cfg
CMD /home/loads/ailoads-loop/bin/ailoads
