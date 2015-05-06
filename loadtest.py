import json
from requests_hawk import HawkAuth
from ailoads.fmwk import scenario, requests


SP_URL = "https://call.stage.mozaws.net/"
SERVER_URL = "https://loop.stage.mozaws.net:443"


@scenario(5)
def place_call():
    # 1. register
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
        print('Could not auth on %r' % SERVER_URL)
        print(resp)
        raise

    # 2. generate a call URL
    resp = requests.post(
            SERVER_URL + '/call-url',
            data=json.dumps({'callerId': 'alexis@mozilla.com'}),
            headers={'Content-Type': 'application/json'},
            auth=hawk_auth
    )


    data = resp.json()
    call_url = data.get('callUrl', data.get('call_url'))
    token = call_url.split('/').pop()

    # 3. initiate call
    resp = requests.post(
        SERVER_URL + '/calls/%s' % token,
        data=json.dumps({"callType": "audio-video"}),
        headers={'Content-Type': 'application/json'}
    )

    call_data = resp.json()

    # 4. list pending calls
    resp = requests.get(
        SERVER_URL + '/calls?version=200',
        auth=hawk_auth)

    calls = resp.json()['calls']



if __name__ == '__main__':
    place_call()
