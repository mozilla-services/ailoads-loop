import random
import json
import os
from base64 import b64encode
import uuid
from urllib.parse import urlparse

from fxa.core import Client
from fxa.tests.utils import TestEmailAccount
from fxa.plugins.requests import FxABrowserIDAuth

from requests_hawk import HawkAuth
from ailoads.fmwk import scenario, requests


SP_URL = os.getenv('LOOP_SP_URL',
                   "https://call.stage.mozaws.net/")
SERVER_URL = os.getenv('LOOP_SERVER_URL',
                       "https://loop.stage.mozaws.net:443")
DEFAULT_FXA_URL = os.getenv("LOOP_FXA_URL",
                            "https://api.accounts.firefox.com/v1")
MAX_NUMBER_OF_PEOPLE_JOINING = 5
PERCENTAGE_OF_REFRESH = 50
PERCENTAGE_OF_MANUAL_LEAVE = 60
PERCENTAGE_OF_MANUAL_ROOM_DELETE = 80
PERCENTAGE_OF_ROOM_CONTEXT = 75


def picked(percent):
    return random.randint(0, 100) < percent


class LoopServer(object):
    def __init__(self):
        self.hawk_auth = None
        self.fxa_server = DEFAULT_FXA_URL
        self.fxa_password = uuid.uuid4().hex
        self.fxa_email = "loop-%s@restmail.net" % self.fxa_password
        self.fxa_auth = self.get_fxa_auth()

    def get_fxa_auth(self):
        acct = TestEmailAccount(self.fxa_email)
        client = Client(self.fxa_server)
        fxa_session = client.create_account(self.fxa_email,
                                            password=self.fxa_password)

        def is_verify_email(m):
            return "x-verify-code" in m["headers"]

        message = acct.wait_for_email(is_verify_email)
        fxa_session.verify_email_code(message["headers"]["x-verify-code"])

        url = urlparse(SERVER_URL)
        audience = "%s://%s" % (url.scheme, url.hostname)

        return FxABrowserIDAuth(
            self.fxa_email,
            password=self.fxa_password,
            audience=audience,
            server_url=self.fxa_server)

    def authenticate(self, data=None):
        if data is None:
            data = {'simple_push_url': SP_URL}
        resp = self.post('/registration', data,
                         auth=self.fxa_auth)
        try:
            self.hawk_auth = HawkAuth(
                hawk_session=resp.headers['hawk-session-token'],
                server_url=SERVER_URL)
        except KeyError:
            print('Could not auth on %r' % SERVER_URL)
            print(resp)
            raise

    def post(self, endpoint, data, auth=None):
        if auth is None:
            auth = self.hawk_auth

        return requests.post(
            SERVER_URL + endpoint,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'},
            auth=auth)

    def get(self, endpoint, auth=None):
        if auth is None:
            auth = self.hawk_auth

        return requests.get(
            SERVER_URL + endpoint,
            headers={'Content-Type': 'application/json'},
            auth=auth)

    def delete(self, endpoint, auth=None):
        if auth is None:
            auth = self.hawk_auth

        return requests.delete(
            SERVER_URL + endpoint,
            headers={'Content-Type': 'application/json'},
            auth=auth)


@scenario(50)
def setup_room():
    """Setting up a room"""
    room_size = MAX_NUMBER_OF_PEOPLE_JOINING

    # 1. register
    server = LoopServer()
    server.authenticate({"simplePushURLs": {"calls": SP_URL,
                                            "rooms": SP_URL}})

    # 2. create room - sometimes with a context
    data = {
        "roomName": "UX Discussion",
        "expiresIn": 1,
        "roomOwner": "Alexis",
        "maxSize": room_size
    }

    if picked(PERCENTAGE_OF_ROOM_CONTEXT):
        del data['roomName']
        data['context'] = {
            "value": b64encode(os.urandom(1024)).decode('utf-8'),
            "alg": "AES-GCM",
            "wrappedKey": b64encode(os.urandom(16)).decode('utf-8')
        }

    resp = server.post('/rooms', data)
    room_token = resp.json().get('roomToken')

    # 3. join room
    num_participants = random.randint(1, room_size)
    data = {"action": "join",
            "displayName": "User1",
            "clientMaxSize": room_size}
    server.post('/rooms/%s' % room_token, data)

    # 4. have other folks join the room as well, refresh and leave
    for x in range(num_participants - 1):
        peer_server = LoopServer()
        peer_server.authenticate()
        data = {"action": "join",
                "displayName": "User%d" % (x + 2),
                "clientMaxSize": room_size}

        peer_server.post('/rooms/%s' % room_token, data)

        if picked(PERCENTAGE_OF_REFRESH):
            peer_server.post('/rooms/%s' % room_token,
                             data={"action": "refresh"})

        if picked(PERCENTAGE_OF_MANUAL_LEAVE):
            peer_server.post('/rooms/%s' % room_token,
                             data={"action": "leave"})

    # 5. leave the room
    server.post('/rooms/%s' % room_token, data={"action": "leave"})

    # 6. delete the room (sometimes)
    if picked(PERCENTAGE_OF_MANUAL_ROOM_DELETE):
        server.delete('/rooms/%s' % room_token)


@scenario(50)
def setup_call():
    """Setting up a call"""
    # 1. register
    server = LoopServer()
    server.authenticate()

    # 2. initiate call
    data = {"callType": "audio-video", "calleeId": server.fxa_email}
    resp = server.post('/calls', data)
    call_data = resp.json()

    # 3. list pending calls
    resp = server.get('/calls?version=200')
    calls = resp.json()['calls']


if __name__ == '__main__':
    setup_room()
    setup_call()
