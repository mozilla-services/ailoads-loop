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


class FXAUser(object):
    def __init__(self):
        self.server = DEFAULT_FXA_URL
        self.password = uuid.uuid4().hex
        self.email = "loop-%s@restmail.net" % self.password
        self.auth = self.get_auth()
        self.hawk_auth = None

    def get_auth(self):
        acct = TestEmailAccount(self.email)
        client = Client(self.server)
        session = client.create_account(self.email,
                                        password=self.password)

        def is_verify_email(m):
            return "x-verify-code" in m["headers"]

        message = acct.wait_for_email(is_verify_email)
        session.verify_email_code(message["headers"]["x-verify-code"])
        url = urlparse(SERVER_URL)
        audience = "%s://%s" % (url.scheme, url.hostname)

        return FxABrowserIDAuth(
            self.email,
            password=self.password,
            audience=audience,
            server_url=self.server)


class LoopConnection(object):

    def __init__(self, user=None):
        if user is None:
            user = FXAUser()
        self.user = user

    def authenticate(self, data=None):
        if data is None:
            data = {'simple_push_url': SP_URL}
        resp = self.post('/registration', data)
        try:
            self.user.hawk_auth = HawkAuth(
                hawk_session=resp.headers['hawk-session-token'],
                server_url=SERVER_URL)
        except KeyError:
            print('Could not auth on %r' % SERVER_URL)
            print(resp)
            raise

    def _auth(self):
        if self.user.hawk_auth is None:
            return self.user.auth
        return self.user.hawk_auth

    def post(self, endpoint, data):
        return requests.post(
            SERVER_URL + endpoint,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'},
            auth=self._auth())

    def get(self, endpoint):
        return requests.get(
            SERVER_URL + endpoint,
            headers={'Content-Type': 'application/json'},
            auth=self._auth())

    def delete(self, endpoint):
        return requests.delete(
            SERVER_URL + endpoint,
            headers={'Content-Type': 'application/json'},
            auth=self._auth())


@scenario(50)
def setup_room():
    """Setting up a room"""
    room_size = MAX_NUMBER_OF_PEOPLE_JOINING

    # 1. register
    conn = LoopConnection()
    conn.authenticate({"simplePushURLs": {"calls": SP_URL,
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

    resp = conn.post('/rooms', data)
    room_token = resp.json().get('roomToken')

    # 3. join room
    num_participants = random.randint(1, room_size)
    data = {"action": "join",
            "displayName": "User1",
            "clientMaxSize": room_size}
    conn.post('/rooms/%s' % room_token, data)

    # 4. have other folks join the room as well, refresh and leave
    for x in range(num_participants - 1):
        peer_conn = LoopConnection()
        peer_conn.authenticate()
        data = {"action": "join",
                "displayName": "User%d" % (x + 2),
                "clientMaxSize": room_size}

        peer_conn.post('/rooms/%s' % room_token, data)

        if picked(PERCENTAGE_OF_REFRESH):
            peer_conn.post('/rooms/%s' % room_token,
                           data={"action": "refresh"})

        if picked(PERCENTAGE_OF_MANUAL_LEAVE):
            peer_conn.post('/rooms/%s' % room_token,
                           data={"action": "leave"})

    # 5. leave the room
    conn.post('/rooms/%s' % room_token, data={"action": "leave"})

    # 6. delete the room (sometimes)
    if picked(PERCENTAGE_OF_MANUAL_ROOM_DELETE):
        conn.delete('/rooms/%s' % room_token)


@scenario(50)
def setup_call():
    """Setting up a call"""
    # 1. register
    conn = LoopConnection()
    conn.authenticate()

    # 2. initiate call
    data = {"callType": "audio-video", "calleeId": conn.user.email}
    resp = conn.post('/calls', data)
    call_data = resp.json()

    # 3. list pending calls
    resp = conn.get('/calls?version=200')
    calls = resp.json()['calls']


if __name__ == '__main__':
    setup_room()
    setup_call()
