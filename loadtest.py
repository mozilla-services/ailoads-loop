import random
import json
import os
import uuid
from base64 import b64encode, urlsafe_b64decode
from six import text_type

from requests_hawk import HawkAuth
from ailoads.fmwk import scenario, requests


SP_URL = os.getenv('LOOP_SP_URL',
                   "https://call.stage.mozaws.net/")
SERVER_URL = os.getenv('LOOP_SERVER_URL',
                       "https://loop.stage.mozaws.net:443")
FXA_BROWSERID_ASSERTION = os.getenv("FXA_BROWSERID_ASSERTION")

MAX_NUMBER_OF_PEOPLE_JOINING = 5
PERCENTAGE_OF_REFRESH = 50
PERCENTAGE_OF_MANUAL_LEAVE = 60
PERCENTAGE_OF_MANUAL_ROOM_DELETE = 80
PERCENTAGE_OF_ROOM_CONTEXT = 75

if not FXA_BROWSERID_ASSERTION:
    raise ValueError("Please define FXA_BROWSERID_ASSERTION env variable.")


def picked(percent):
    return random.randint(0, 100) < percent


def base64url_decode(input):
    if isinstance(input, text_type):
        input = input.encode('utf-8')
    rem = len(input) % 4

    if rem > 0:
        input += b'=' * (4 - rem)

    return urlsafe_b64decode(input)


def extract_email_from_assertion(assertion):
    fragment = assertion.split('.')[1]
    decoded_fragment = base64url_decode(fragment).decode('utf-8')
    info = json.loads(decoded_fragment)
    email = info['fxa-verifiedEmail']
    return email

FXA_EMAIL = extract_email_from_assertion(FXA_BROWSERID_ASSERTION)

_CONNECTIONS = {}


def get_connection(id=None):
    if id is None or id not in _CONNECTIONS:
        id = uuid.uuid4().hex
        conn = LoopConnection(id)
        _CONNECTIONS[id] = conn

    return _CONNECTIONS[id]


class LoopConnection(object):

    def __init__(self, id):
        self.id = id
        self.headers = {
            "Authorization": "BrowserID %s" % FXA_BROWSERID_ASSERTION,
            'Content-Type': 'application/json'
        }
        self.timeout = 30
        self.authenticated = False
        self.user_hawk_auth = None

    def authenticate(self, data=None):
        if self.authenticated:
            return
        if data is None:
            data = {'simple_push_url': SP_URL}
        resp = self.post('/registration', data)
        resp.raise_for_status()
        try:
            self.user_hawk_auth = HawkAuth(
                hawk_session=resp.headers['hawk-session-token'],
                server_url=SERVER_URL)
        except KeyError:
            print('Could not auth on %r' % SERVER_URL)
            print(resp)
            raise
        self.authenticated = True

    def _auth(self):
        headers = self.headers.copy()
        result = {'headers': headers}
        if self.user_hawk_auth:
            del headers['Authorization']
            result['auth'] = self.user_hawk_auth
        return result

    def post(self, endpoint, data):
        return requests.post(
            SERVER_URL + endpoint,
            data=json.dumps(data),
            timeout=self.timeout,
            **self._auth())

    def get(self, endpoint):
        return requests.get(
            SERVER_URL + endpoint,
            timeout=self.timeout,
            **self._auth())

    def delete(self, endpoint):
        return requests.delete(
            SERVER_URL + endpoint,
            timeout=self.timeout,
            **self._auth())


@scenario(95)
def firefox_starts():
    # Authenticate the user
    resp = requests.get(SERVER_URL + '/push-server-config', timeout=30)
    resp.raise_for_status()

    resp = requests.post(
        SERVER_URL + '/registration', timeout=30,
        data=json.dumps({"simplePushURLs": {"calls": SP_URL,
                                            "rooms": SP_URL}}))
    resp.raise_for_status()


@scenario(4)
def setup_room():
    """Setting up a room"""
    room_size = MAX_NUMBER_OF_PEOPLE_JOINING

    # 1. register
    conn = get_connection('user1')
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
    resp.raise_for_status()
    room_token = resp.json().get('roomToken')

    # 3. join room
    num_participants = random.randint(1, room_size)
    data = {"action": "join",
            "displayName": "User1",
            "clientMaxSize": room_size}
    resp = conn.post('/rooms/%s' % room_token, data)
    resp.raise_for_status()

    # 4. have other folks join the room as well, refresh and leave
    for x in range(num_participants - 1):
        peer_conn = get_connection('user%d' % (x+2))
        peer_conn.authenticate()
        data = {"action": "join",
                "displayName": "User%d" % (x + 2),
                "clientMaxSize": room_size}

        resp = peer_conn.post('/rooms/%s' % room_token, data)
        resp.raise_for_status()

        if picked(PERCENTAGE_OF_REFRESH):
            resp = peer_conn.post('/rooms/%s' % room_token,
                                  data={"action": "refresh"})
            resp.raise_for_status()

        if picked(PERCENTAGE_OF_MANUAL_LEAVE):
            resp = peer_conn.post('/rooms/%s' % room_token,
                                  data={"action": "leave"})
            resp.raise_for_status()

    # 5. leave the room
    resp = conn.post('/rooms/%s' % room_token, data={"action": "leave"})
    resp.raise_for_status()

    # 6. delete the room (sometimes)
    if picked(PERCENTAGE_OF_MANUAL_ROOM_DELETE):
        resp = conn.delete('/rooms/%s' % room_token)
        resp.raise_for_status()


@scenario(1)
def setup_call():
    """Setting up a call"""
    # 1. register
    conn = get_connection('user1')
    conn.authenticate()

    # 2. initiate call
    data = {"callType": "audio-video", "calleeId": FXA_EMAIL}
    resp = conn.post('/calls', data)
    resp.raise_for_status()
    resp.json()

    # 3. list pending calls
    resp = conn.get('/calls?version=200')
    resp.raise_for_status()
    resp.json()['calls']
