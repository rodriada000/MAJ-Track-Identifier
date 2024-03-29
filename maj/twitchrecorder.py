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
import logging
from streamlink import Streamlink
from maj.vpnrotator import VpnRotator

log = logging.getLogger(__name__)

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

            expires_in = keys.get('expires_in', 0) # this is in seconds

            self.oauth_token = keys.get('access_token','')
            self.expiration_date = datetime.datetime.now() + datetime.timedelta(0, expires_in)
            return True
        except Exception as e:
            log.error(e)
            return False

    def init_paths(self):
        # path to recorded stream
        self.recorded_path = os.path.join(self.root_path, "recorded", self.username)

        # create directory for recordedPath if not exist
        if(os.path.isdir(self.recorded_path) is False):
            os.makedirs(self.recorded_path)

    def is_user_online(self):
        return self.get_user() is not None

    def get_user(self):
        headers = {
            'Client-ID': self.client_id,
            'Authorization': 'Bearer ' + self.oauth_token
        }

        stream = requests.get('https://api.twitch.tv/helix/streams?user_login=' + self.username, headers=headers)
        stream_json = stream.json()


        if len(stream_json['data']) == 1:
            return stream_json['data'][0]
        else:
            return None

    def get_stream_title(self):
        user = self.get_user()
        if user is not None:
            return user.get('title', '')
        else:
            return ''

    async def record(self, length):
        filename = self.username + " - " + datetime.datetime.now().strftime("%Y-%m-%d %Hh%Mm%Ss") + ".mp4"
        
        # clean filename from unecessary characters
        filename = "".join(x for x in filename if x.isalnum() or x in [" ", "-", "_", "."])
        
        recorded_filename = os.path.join(self.recorded_path, filename)
        
        log.info("output path: " + recorded_filename)

        self.is_recording = True
        self.is_blocked = False

        # start streamlink process
        cmds = ["streamlink", "twitch.tv/" + self.username, self.quality, "-o", recorded_filename, "--http-header", "Authorization=Bearer " + self.oauth_token, "--http-header", "Client-Id=" + self.client_id, "--http-header", "Origin=https://www.twitch.tv", "--twitch-disable-ads"]
        print(cmds)
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
                    log.debug(last_size)

                if last_size > SIZE_THRESHOLD: 
                    self.is_blocked = True
                    break # stop recording after filesize limit reached
        
        log.info('\n\nkilling streamlink ...')
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

    stream = twitch_recorder.get_user()

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

    stream = twitch_recorder.get_user()
    print(stream)

    if stream is not None:
        path = await twitch_recorder.record(20)

    print("is_blocked: {0}".format(twitch_recorder.is_blocked))

if __name__ == "__main__":
    asyncio.run(sample_record())