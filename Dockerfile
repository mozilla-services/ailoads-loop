# Mozilla Loop Load-Tester
FROM python:3.5

MAINTAINER Remy HUBSCHER

RUN \
    apt-get update; \
    apt-get install -y git build-essential make libssl-dev libffi-dev; \
    git clone https://github.com/mozilla-services/ailoads-loop /home/loop; \
    cd /home/loop; \
    make build; \
	apt-get remove -y -qq git build-essential make libssl-dev libffi-dev; \
    apt-get autoremove -y -qq; \
    apt-get clean -y

WORKDIR /home/loop

# run the test
CMD venv/bin/ailoads -v -d $LOOP_DURATION -u $LOOP_NB_USERS
