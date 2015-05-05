import json
from requests_hawk import HawkAuth
from ailoads.fmwk import scenario, requests


SP_URL = "https://call.stage.mozaws.net/"
SERVER_URL = "https://loop.stage.mozaws.net:443"


def register():
    data = {'simple_push_url': SP_URL}

    resp = requests.post(
        SERVER_URL + '/registration',
        data=json.dumps(data),
        headers={'Content-Type': 'application/json'})

    try:
        hawk_auth = HawkAuth(
            hawk_session=resp.headers['hawk-session-token'],
            server_url=SERVER_URL)
    except KeyError:
        print resp
        raise
    else:
        self.incr_counter("register")
        return self.hawk_auth


@scenario(5)
def place_call():
    return requests.get('http://localhost:8000')


if __name__ == '__main__':
    place_call()
