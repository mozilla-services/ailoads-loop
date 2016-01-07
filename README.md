# ailoads-loop

loop load test based on ailoads

## Requirements

- Python 3.4


## How to run the loadtest?

### For stage

    make setup_random test

or for a longer one:

    make setup_random test-heavy

### For production

    make setup_existing -e FXA_EXISTING_EMAIL=test-account-email@example.com
    make test -e LOOP_SERVER_URL=http://localhost:5000

or all at once:

    make setup_existing test -e \
        FXA_EXISTING_EMAIL=test-account-email@example.com \
        LOOP_SERVER_URL=http://localhost:5000


## How to build the docker image?

    make docker-build


## How to run the docker image?

    make docker-run


## How to clean the repository?

    make clean
