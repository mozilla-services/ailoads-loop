HERE = $(shell pwd)
BIN = $(HERE)/venv/bin
PYTHON = $(BIN)/python3.5

INSTALL = $(BIN)/pip install

LOOP_SERVER_URL = https://loop.stage.mozaws.net:443
FXA_EXISTING_EMAIL =


.PHONY: all test build

all: build test

$(PYTHON):
	$(shell basename $(PYTHON)) -m venv $(VTENV_OPTS) venv
	$(BIN)/pip install requests requests_hawk flake8 PyFxA
	$(BIN)/pip install https://github.com/tarekziade/ailoads/archive/master.zip
build: $(PYTHON)

loadtest.env:
	$(BIN)/fxa-client -c --browserid --prefix loop-server --audience https://loop.stage.mozaws.net --out loadtest.env

refresh:
	@rm -f loadtest.env

setup_random: refresh loadtest.env

setup_existing:
	$(BIN)/fxa-client --browserid --auth "$(FXA_EXISTING_EMAIL)" --account-server https://api.accounts.firefox.com/v1 --audience https://loop.stage.mozaws.net --out loadtest.env


test: build loadtest.env
	bash -c "source loadtest.env && LOOP_SERVER_URL=$(LOOP_SERVER_URL) $(BIN)/ailoads -v -d 30"
	$(BIN)/flake8 loadtest.py

test-heavy: build loadtest.env
	bash -c "source loadtest.env && LOOP_SERVER_URL=$(LOOP_SERVER_URL) $(BIN)/ailoads -v -d 300 -u 10"

clean: refresh
	rm -fr venv/ __pycache__/

docker-build:
	docker build -t loop/loadtest .

docker-run: loadtest.env
	bash -c "source loadtest.env; docker run -e LOOP_DURATION=30 -e LOOP_NB_USERS=4 -e FXA_BROWSERID_ASSERTION=\$${FXA_BROWSERID_ASSERTION} loop/loadtest"

configure: build loadtest.env
	@bash loop.tpl

docker-export:
	docker save "loop/loadtest:latest" | bzip2> loop-latest.tar.bz2
