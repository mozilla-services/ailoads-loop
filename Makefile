HERE = $(shell pwd)
BIN = $(HERE)/bin
PYTHON = $(BIN)/python

INSTALL = $(BIN)/pip install 


.PHONY: all test build 

all: build test

$(PYTHON):
	virtualenv $(VTENV_OPTS) .

build: $(PYTHON)
	$(BIN)/pip install requests requests_hawk
	$(BIN)/pip install https://github.com/tarekziade/ailoads/archive/master.zip


test: build
	$(BIN)/pip install flake8 tox
	$(BIN)/flake8 ailoads
	$(BIN)/tox

build_docker:
	docker build -t loop/loadtest .
