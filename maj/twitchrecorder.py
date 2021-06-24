# This code is based on tutorial by slicktechies modified as needed to use oauth token from Twitch.
# You can read more details at: https://www.junian.net/2017/01/how-to-record-twitch-streams.html
# original code is from https://slicktechies.com/how-to-watchrecord-twitch-streams-using-livestreamer/

import requests
import os
import time
import json
import sys
import subprocess
import datetime
import getopt
import asyncio
from streamlink import Streamlink
from maj.vpnrotator import VpnRotator

SIZE_THRESHOLD = 1000000 # size of file in bytes (when to stop recording)

class TwitchRecorder:
    def __init__(self, client_id, client_secret, username, root_path, quality='audio_only'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth_token = ""
        self.expiration_date = None
        self.refresh = 5.0
        self.root_path = root_path
        self.is_recording = False
        self.is_blocked = False
        
        self.username = username
        self.quality = quality

        self.init_paths()

    def authorize(self, saved_token, saved_expiration):
        self.oauth_token = saved_token
        self.expiration_date = datetime.date.fromisoformat(saved_expiration)

        if datetime.date.today() < self.expiration_date:
            return False # token not expired so no need to refresh it

        body = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            "grant_type": 'client_credentials'
        }

        try:
            r = requests.post('https://id.twitch.tv/oauth2/token', body)

            keys = r.json()
            print(keys) # for debugging

            expires_in = keys.get('expires_in', 0) # this is in seconds

            self.oauth_token = keys.get('access_token','')
            self.expiration_date = datetime.datetime.now() + datetime.timedelta(0, expires_in)
            return True
        except Exception as e:
            print(e)
            return False

    def init_paths(self):
        # path to recorded stream
        self.recorded_path = os.path.join(self.root_path, "recorded", self.username)

        # create directory for recordedPath if not exist
        if(os.path.isdir(self.recorded_path) is False):
            os.makedirs(self.recorded_path)

    def check_user(self):
        headers = {
            'Client-ID': self.client_id,
            'Authorization': 'Bearer ' + self.oauth_token
        }

        stream = requests.get('https://api.twitch.tv/helix/streams?user_login=' + self.username, headers=headers)
        stream_json = stream.json()


        # print(stream_json)

        if len(stream_json['data']) == 1:
            print(self.username + ' is live: ' + stream_json['data'][0]['title'] + ' playing ' + stream_json['data'][0]['game_name'])
            return stream_json['data'][0]
        else:
            print(self.username + ' is not live')
            return None


    async def record(self, length):
        filename = self.username + " - " + datetime.datetime.now().strftime("%Y-%m-%d %Hh%Mm%Ss") + ".mp4"
        
        # clean filename from unecessary characters
        filename = "".join(x for x in filename if x.isalnum() or x in [" ", "-", "_", "."])
        
        recorded_filename = os.path.join(self.recorded_path, filename)
        
        print("output path: " + recorded_filename)

        self.is_recording = True
        self.is_blocked = False

        # start streamlink process
        cmds = ["streamlink", "twitch.tv/" + self.username, self.quality, "-o", recorded_filename, "--http-header", "Authorization=Bearer " + self.oauth_token, "--http-header", "Client-Id=" + self.client_id, "--http-header", "Origin=https://www.twitch.tv"]
        p = subprocess.Popen(cmds, shell=False, stdin=None, stdout=None, stderr=None, close_fds=True)
        
        sleep_time = 5 + length # add 5 for the initial startup of the process and loading the stream
        slept = 0
        last_size = 0

        while slept < sleep_time:
            await asyncio.sleep(1)
            slept += 1
            if os.path.exists(recorded_filename):
                if os.path.getsize(recorded_filename) > last_size:
                    last_size = os.path.getsize(recorded_filename)
                    print(last_size)

                if last_size > SIZE_THRESHOLD: 
                    self.is_blocked = True
                    break # stop recording after filesize limit reached
        
        print('\n\nkilling streamlink ...')
        p.kill()
        p.wait()

        self.is_recording = False
        return recorded_filename


async def sample_record():
    config = {}

    with open('.\\config.json') as f:
        config = json.load(f)

    twitch_recorder = TwitchRecorder(config['botClientID'], config['botSecret'], config['channel'], config['recordedSavePath'])
    twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])

    stream = twitch_recorder.check_user()

    print(stream)

    if stream is not None:
        path = await twitch_recorder.record(20)

    print("is_blocked: {0}".format(twitch_recorder.is_blocked))

async def sample_record_with_vpn():
    config = {}

    with open('.\\config.json') as f:
        config = json.load(f)

    twitch_recorder = TwitchRecorder(config['botClientID'], config['botSecret'], config['channel'], config['recordedSavePath'])
    twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])

    vpn = VpnRotator(config['vpnConfigFolders'], config['vpnUserPwdConfigPath'])
    vpn.connect_random()

    await asyncio.sleep(7) # wait for vpn to full init/connect

    stream = twitch_recorder.check_user()
    print(stream)

    if stream is not None:
        path = await twitch_recorder.record(20)

    print("is_blocked: {0}".format(twitch_recorder.is_blocked))

# if __name__ == "__main__":
#     asyncio.run(sample_record_with_vpn())