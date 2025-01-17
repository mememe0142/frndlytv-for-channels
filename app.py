#!/usr/bin/python3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import requests

PORT = 80
USERNAME = os.getenv('USERNAME', '').strip()
PASSWORD = os.getenv('PASSWORD', '').strip()
IP_ADDR = os.getenv('IP', '').strip()

LOGO_SIZE = 110
PLAYLIST_URL = 'playlist.m3u'
PLAY_URL = 'play'
STATUS_URL = ''

HEADERS = {
    'user-agent': 'okhttp/3.12.5',
    'box-id': 'SHIELD30X8X4X0',
    'tenant-code': 'frndlytv',
}

if IP_ADDR:
    HEADERS['x-forwarded-for'] = IP_ADDR

LIVE_MAP = {
    10: [58812, 'the_weather_channel'],
    17: [82773, 'insp'],
    15: [66143, 'up_tv'],
    1: [66268, 'hallmark_channel'],
    4: [70113, 'pixl'],
    2: [46710, 'hallmark_movies___mysteries'],
    3: [105723, 'hallmark_drama'],
    22: [73413, 'fetv'],
    20: [82563, 'get_tv'],
    23: [113430, 'circle'],
    18: [71764, 'byutv'],
    6: [68827, 'game_show_network'],
    19: [81289, 'recipe_tv'],
    16: [120084, 'curiositystream'],
    21: [99988, 'local_now'],
    7: [46737, 'outdoor_channel'],
    8: [60399, 'sportsman_channel'],
    9: [64046, 'world_fishing_network'],
    11: [119335, 'babyfirst_tv'],
    12: [60222, 'qvc'],
}

def login():
    params = {
        'box_id': HEADERS['box-id'],
        'device_id': 43,
        'tenant_code': HEADERS['tenant-code'],
        'device_sub_type': 'nvidia,8.1.0,7.4.4',
        'product': HEADERS['tenant-code'],
        'display_lang_code': 'eng',
        'timezone': 'Pacific/Auckland',
    }

    HEADERS['session-id'] = requests.get('https://frndlytv-api.revlet.net/service/api/v1/get/token', params=params, headers=HEADERS).json()['response']['sessionId']
    print(HEADERS['session-id'])

    payload = {
        "login_key": PASSWORD,
        "login_id": USERNAME,
        "login_mode": 1,
        "os_version": "8.1.0",
        "app_version": "7.4.4",
        "manufacturer": "nvidia"
    }

    data = requests.post('https://frndlytv-api.revlet.net/service/api/auth/signin', json=payload, headers=HEADERS).json()
    if not data['status']:
        print(data['error']['message'])
    else:
        print("logged in!")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {
            PLAYLIST_URL: self._playlist,
            PLAY_URL: self._play,
            STATUS_URL: self._status,
        }

        func = self.path.split('/')[1]
        if func not in routes:
            self.send_response(404)
            self.end_headers()
            return

        routes[func]()

    def _play(self):
        id = int(self.path.split('/')[-1])
        if id not in LIVE_MAP:
            print("Could not find that channel")
            self.send_response(404)
            self.end_headers()
            return

        slug = LIVE_MAP[id][1]
        data = requests.get(f'https://frndlytv-api.revlet.net/service/api/v1/page/stream?path=channel%2Flive%2F{slug}&code=channel%2Flive%2F{slug}&include_ads=false&is_casted=true', headers=HEADERS).json()

        self.send_response(302)
        self.send_header('location', data['response']['streams'][0]['url'])
        self.end_headers()
    
    def _playlist(self):
        host = self.headers.get('Host')
        rows = requests.get('https://frndlytv-api.revlet.net/service/api/v1/tvguide/channels?skip_tabs=0', headers=HEADERS).json()['response']['data']

        self.send_response(200)
        self.end_headers()

        self.wfile.write(b'#EXTM3U\n')
        for row in rows:
            id = row['id']
            if id not in LIVE_MAP:
                continue

            name = row['display']['title']
            gracenote_id = LIVE_MAP[id][0]
            url = f'http://{host}/{PLAY_URL}/{id}'
            bucket, path = row['display']['imageUrl'].split(',')
            logo = f'https://d229kpbsb5jevy.cloudfront.net/frndlytv/{LOGO_SIZE}/{LOGO_SIZE}/content/{bucket}/logos/{path}'

            self.wfile.write(f'#EXTINF:-1 channel-id="frndly-{id}" tvg-logo="{logo}" tvc-guide-stationid="{gracenote_id}",{name}\n{url}\n'.encode('utf8'))

    def _status(self):
        self.send_response(200)
        self.end_headers()
        host = self.headers.get('Host')
        session_id = HEADERS.get('session-id')
        self.wfile.write(f'Playlist URL: http://{host}/{PLAYLIST_URL}\nFrndlytv Session ID: {session_id}'.encode('utf8'))

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run():
    server = ThreadingSimpleServer(('0.0.0.0', PORT), Handler)
    server.serve_forever()

if __name__ == '__main__':
    login()
    run()
