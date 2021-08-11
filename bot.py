import datetime
import json
from time import sleep
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import SongList
from maj.vpnrotator import VpnRotator
from maj.pollvote import MajPoll
from maj.twitchbot import TwitchBot
from maj.utils.botreplys import load_chat_intents

config = {}

with open('config.json', 'r') as f:
    config = json.load(f)

# setup vpn rotator to connect to different vpns when twitch recording is blocked
vpn = VpnRotator(config['vpnConfigFolders'], config['vpnUserPwdConfigPath'])

# set up list to cache songs (will load from file if exists)
playlist = SongList(config['recordedSavePath'], config['channel'], datetime.datetime.today())

# set up recorder
twitch_recorder = TwitchRecorder(config['botClientID'], config['botSecret'], config['channel'], config['recordedSavePath'])

# set up music identifier
music_identifier = Identifier(config['acrKey'], config['acrSecret'], config['acrHostUrl'])

# set up the bot
bot = TwitchBot(
    config=config,
    playlist=playlist,
    recorder=twitch_recorder,
    identifier=music_identifier,
    vpn=vpn,
    irc_token=config['botIrcToken'],
    client_id=config['botClientID'],
    nick=config['botUsername'],
    prefix='!',
    case_insensitive=True,
    initial_channels=['#' + config['channel']]
)

if __name__ == "__main__":

    load_chat_intents('./maj/utils/intents.json')

    token_updated = bot.twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])    

    # save new oauth token if fetched new one
    if token_updated:
        with open('config.json', 'w') as f:
            f.write(json.dumps(config, indent = 4))

    try:
        while bot.twitch_recorder.check_user() is None:
            print('waiting for channel to be online ...')
            sleep(60)
    except KeyboardInterrupt:
        pass

    # update the datetime to match when user goes online
    if not bot.playlist.has_started:
        bot.playlist.setlist_start = datetime.datetime.today()
        bot.playlist.has_started = True

    # blocking call to have twitch bot run
    try:
        bot.run()
    except Exception:
        pass

    if bot.vpn is not None and bot.vpn.is_connected:
        bot.vpn.disconnect()

