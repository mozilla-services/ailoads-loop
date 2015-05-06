import json
from requests_hawk import HawkAuth
from ailoads.fmwk import scenario, requests


SP_URL = "https://call.stage.mozaws.net/"
SERVER_URL = "https://loop.stage.mozaws.net:443"


class LoopServer(object):
    def __init__(self):
        self.auth = None

    def authenticate(self, data=None):
        if data is None:
            data = {'simple_push_url': SP_URL}
        resp = self.post('/registration', data)
        try:
            self.auth = HawkAuth(
                hawk_session=resp.headers['hawk-session-token'],
                server_url=SERVER_URL)
        except KeyError:
            print('Could not auth on %r' % SERVER_URL)
            print(resp)
            raise

    def post(self, endpoint, data):
        return requests.post(
            SERVER_URL + endpoint,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'},
            auth=self.auth)

    def get(self, endpoint):
        return requests.get(
            SERVER_URL + endpoint,
            headers={'Content-Type': 'application/json'},
            auth=self.auth)


@scenario(5)
def setup_call():
    """Setting up a call"""
    # 1. register
    server = LoopServer()
    server.authenticate()

    # 2. generate a call URL
    data = {'callerId': 'alexis@mozilla.com'}
    resp = server.post('/call-url', data)
    data = resp.json()
    call_url = data.get('callUrl', data.get('call_url'))
    token = call_url.split('/').pop()

    # 3. initiate call
    data = {"callType": "audio-video"}
    resp = server.post('/calls/%s' % token, data)
    call_data = resp.json()

    # 4. list pending calls
    resp = server.get('/calls?version=200')
    calls = resp.json()['calls']



if __name__ == '__main__':
    setup_call()
