import base64
import hashlib
import hmac
import os
import sys
import time
import requests
import json

class Identifier:
    def __init__(self, key, secret, url):
        self.access_key = key
        self.access_secret = secret
        self.url = url
        self.is_identifying = False

        self.http_method = "POST"
        self.http_uri = "/v1/identify"
        self.signature_version = "1"

    def identify(self, file_path, data_type='audio'):
        
        self.is_identifying = True

        timestamp = time.time()

        string_to_sign = self.http_method + "\n" + self.http_uri + "\n" + self.access_key + "\n" + data_type + "\n" + self.signature_version + "\n" + str(
            timestamp)

        sign = base64.b64encode(hmac.new(self.access_secret.encode('ascii'), string_to_sign.encode('ascii'),
                                        digestmod=hashlib.sha1).digest()).decode('ascii')

        f = open(file_path, "rb")
        sample_bytes = os.path.getsize(file_path)

        files = [
            ('sample', ('sample.mp4', f, 'audio/mpeg'))
        ]
        data = {'access_key': self.access_key,
                'sample_bytes': sample_bytes,
                'timestamp': str(timestamp),
                'signature': sign,
                'data_type': data_type,
                "signature_version": self.signature_version}

        r = requests.post(self.url, files=files, data=data)
        r.encoding = "utf-8"
        
        self.is_identifying = False

        if r.status_code == 200:
            response = r.json()
            return response
        else:
            print(str(r.status_code) + ' - ' + r.reason)
            return None

    def get_song_info_from_response(self, response):
        if response is None or response['status']['msg'] != "Success":
            print(response)
            return None
        
        if len(response['metadata']['music']) < 1:
            print(response)
            return None
        else:
            song = response['metadata']['music'][0]
            title = song['title']
            artists = [v['name'] for v in song['artists']] 
            album = song['album']['name']
            
            return {'title': title, 'artists': artists, 'album': album, 'multipleResults': len(response['metadata']['music']) > 1}


def sample_get():
    """
    Sample function to show usage of Identifier
    """
    config = {}

    with open('..\\config.json') as f:
        config = json.load(f)

    # GET FROM ACR
    access_key = config['acrKey']
    access_secret = config['acrSecret']
    requrl = config['acrHostUrl']

    identifier = Identifier(access_key, access_secret, requrl)
    response = identifier.identify('F:\\twitch\\recorded\\relaxbeats\\sample.mp4')
    info = identifier.get_song_info_from_response(response)

    if info is None:
        print("Could not identify the current song ...")
    else:
        print(info)
        print("Currently playing: " + info['title'] + '\nBy artist(s): ' + ';'.join(info['artists']) + '\nAlbum: ' + info['album'])