import os
import datetime
import json
import asyncio
import random
from time import sleep
from twitchio.ext import commands
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import Song,SongList
from maj.vpnrotator import VpnRotator
from maj.utils import botreplys


bot_status = {'hasGreeted': False, 'isIdentifying': False, 'triggerCount': 0, 'isSilenced': True}
config = {}

with open('config.json', 'r') as f:
    config = json.load(f)

# set up the bot
bot = commands.Bot(
    irc_token=config['botIrcToken'],
    client_id=config['botClientID'],
    nick=config['botUsername'],
    prefix='!',
    initial_channels=['#' + config['channel']]
)

# setup vpn rotator to connect to different vpns when twitch recording is blocked
vpn = VpnRotator(config['vpnConfigFolders'], config['vpnUserPwdConfigPath'])

# set up list to cache songs (will load from file if exists)
playlist = SongList(config['recordedSavePath'], config['channel'], datetime.datetime.today())

# set up recorder
twitch_recorder = TwitchRecorder(config['botClientID'], config['botSecret'], config['channel'], config['recordedSavePath'])

# set up music identifier
music_identifier = Identifier(config['acrKey'], config['acrSecret'], config['acrHostUrl'])


@bot.event
async def event_ready():
    'Called once when the bot goes online.'
    global bot_status

    print(f"{config['botUsername']} is online!")
    if bot_status['hasGreeted'] is False:
        bot_status['hasGreeted'] = True

        if config['print_only'] is False:
            ws = bot._ws  # this is only needed to send messages within event_ready
            await ws.send_privmsg(config['channel'], "{0} Type '!track' to identify the current song playing.".format(botreplys.get_greeting(datetime.datetime.today())))

@bot.event
async def event_message(ctx):
    'Runs every time a message is sent in chat.'

    # make sure the bot ignores itself and the streamer
    if ctx.author.name.lower() == config['botUsername'].lower():
        return

    await bot.handle_commands(ctx)
    # to send message within event_message: # await ctx.channel.send(ctx.content) # 

@bot.command(name='track', aliases=['playing', 'tune', 'TRACK', 'thong'])
async def track(ctx):
    global config
    global bot_status

    if bot_status['isIdentifying'] is True or twitch_recorder.is_recording or music_identifier.is_identifying:
        print('already trying to identify!')
        bot_status['triggerCount'] += 1

        if bot_status['triggerCount'] >= 5:
            bot_status['triggerCount'] = 0 # reset count so message sent every 5 times someone sends '!track' 
            await send_message(ctx, botreplys.get_already_listening_reply())

        return

    if len(playlist.songs) > 0:
        elapsedTime = datetime.datetime.now() - playlist.songs[-1].last_timestamp
        if elapsedTime.total_seconds() < 60:
            print("already identified a song less than 60 seconds ago ...")
            await send_message(ctx, playlist.get_last_song_msg())
            return

    found = False
    trys = 0
    while found is False and trys < 10:
        found = await try_identify(ctx)
        await asyncio.sleep(5)
        trys += 1
    
    if not found:
        print('exceeded number of retrys ...')

async def try_identify(ctx):
    global bot_status

    bot_status['isIdentifying'] = True
    bot_status['triggerCount'] = 0

    try:
        file_path = await twitch_recorder.record(20)

        if twitch_recorder.is_blocked and config['enableVpnRotation']:
            print("recording blocked. switching vpn ...")
            # connect to a different vpn and try again
            if vpn.is_connected: 
                vpn.disconnect()
                await asyncio.sleep(2) # sleep to let disconnect finish
            
            vpn.connect_random()
            await asyncio.sleep(7) # sleep to let init/connect 

            print ('re-recording audio ...')
            file_path = await twitch_recorder.record(20)
            print('blocked again: {0}'.format(twitch_recorder.is_blocked))

    except Exception as e:
        print(e)
        twitch_recorder.is_recording = False
        file_path = None

    if file_path is None or not os.path.exists(file_path):
        bot_status['isIdentifying'] = False
        await send_message(ctx, botreplys.get_trouble_listening_reply(), force_quiet=bot_status['isSilenced'])
        return False

    try:
        response = music_identifier.identify(file_path)
        info = music_identifier.get_song_info_from_response(response)
    except Exception as e:
        print(e)
        music_identifier.is_identifying = False
        info = None

    if info is None:
        bot_status['isIdentifying'] = False
        msg = botreplys.get_trouble_listening_reply() if twitch_recorder.is_blocked else botreplys.get_unknown_song_reply()
        await send_message(ctx, msg, force_quiet=bot_status['isSilenced'])
        return False
        
    song = Song(info)
    playlist.add(song)
    msg = ""
    if info['multipleResults'] is True:
        msg += "(I think) "
    msg += f'Currently playing: "{song.title}" ║ Artist(s): {", ".join(song.artists)}  ║ Album: {song.album}'
    
    bot_status['isIdentifying'] = False
    await send_message(ctx, msg)
    return True


@bot.command(name='majhelp', aliases=['bothelp'])
async def majhelp(ctx):
    await send_message(ctx, 'Type "!track" to identify the current song playing. "!last" for last song identified or "!last X" to get last X songs identified.')

@bot.command(name='add')
async def add(ctx):
    track_info = ctx.content[5:].split(';')
    song = Song({'title': track_info[0], 'artists': [track_info[1]], 'album': ''})
    playlist.add(song)
    
    msg = f'Added: "{song.title}" ║ Artist(s): {", ".join(song.artists)}'
    await send_message(ctx, msg)

@bot.command(name="lastsong", aliases=["last"])
async def lastsong(ctx):

    if len(playlist.songs) == 0:
        return

    chat_msgs = ctx.content.split(' ')
    num_tracks = 1

    if len(chat_msgs) > 1 and chat_msgs[1].isnumeric():
        num_tracks = int(chat_msgs[1])
        if num_tracks < 1 or num_tracks >= len(playlist.songs):
            num_tracks = 1 # ignore any bad input and default it to last 1 track 


    if num_tracks == 1:
        print(playlist.get_last_song_msg())
        await send_message(ctx, playlist.get_last_song_msg())
    else:
        messages = []
        msg_reply = f"The last {num_tracks} tracks played (most recent first) --> "
        for i in range(1, num_tracks + 1):
            song_info = playlist.songs[-i].formatted_str()
            if len(msg_reply + song_info + f' @ {playlist.songs[-i].get_last_identified_in_minutes()}  ██   ') >= 500:
                messages.append(msg_reply)
                msg_reply = ""
            
            msg_reply += song_info + f' @ {playlist.songs[-i].get_last_identified_in_minutes()}  ██   '
        messages.append(msg_reply)

        await send_message_batch(ctx, messages)

@bot.command(name='setlist')
async def setlist(ctx):
    msg = "(Title | Artists | Album) --> "
    messages = []
    seperator = ' ██   '
    for song in playlist.songs:
        if len(msg + song.formatted_str() + seperator) >= 500:
            messages.append(msg)
            msg = ""
        
        msg += song.formatted_str() + seperator
    
    messages.append(msg)

    await send_message_batch(ctx, messages)

@bot.command(name='quiet')
async def quiet(ctx):
    global bot_status
    bot_status['isSilenced'] = True

    chat_msgs = ctx.content.split(' ')

    if len(chat_msgs) > 1 and chat_msgs[1] == "off":
        bot_status['isSilenced'] = False

async def send_message_batch(ctx, messages):
    for m in messages:
        await send_message(ctx, m)
        await asyncio.sleep(1.5 + random.random())

async def send_message(ctx, message, force_quiet=False):
    print(message)
    if config['print_only'] or force_quiet:
        return
    await ctx.send(message)    



if __name__ == "__main__":

    token_updated = twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])

    # save new oauth token if fetched new one
    if token_updated:
        with open('config.json', 'w') as f:
            f.write(json.dumps(config, indent = 4))

    try:
        while twitch_recorder.check_user() is None:
            print('waiting for channel to be online ...')
            sleep(60)
    except KeyboardInterrupt:
        pass

    # blocking call to have twitch bot run
    if twitch_recorder.check_user() is not None:
        try:
            bot.run()
        except Exception:
            pass

    if vpn.is_connected:
        vpn.disconnect()