import random
import json
import os
from base64 import b64encode

from requests_hawk import HawkAuth
from ailoads.fmwk import scenario, requests


SP_URL = os.getenv('LOOP_SP_URL',
                   "https://call.stage.mozaws.net/")
SERVER_URL = os.getenv('LOOP_SERVER_URL',
                       "https://loop.stage.mozaws.net:443")
MAX_NUMBER_OF_PEOPLE_JOINING = 5
PERCENTAGE_OF_REFRESH = 50
PERCENTAGE_OF_MANUAL_LEAVE = 60
PERCENTAGE_OF_MANUAL_ROOM_DELETE = 80
PERCENTAGE_OF_ROOM_CONTEXT = 75


def picked(percent):
    return random.randint(0, 100) < percent


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

    def delete(self, endpoint):
        return requests.delete(
            SERVER_URL + endpoint,
            headers={'Content-Type': 'application/json'},
            auth=self.auth)


@scenario(50)
def setup_room():
    """Setting up a room"""
    room_size = MAX_NUMBER_OF_PEOPLE_JOINING

    # 1. register
    server = LoopServer()
    server.authenticate({"simplePushURLs": {
                            "calls": SP_URL,
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
    setup_room()
    setup_call()
