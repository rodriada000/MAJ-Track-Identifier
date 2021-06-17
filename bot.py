import os
import pathlib
import datetime
import json
import asyncio
import random
from twitchio.ext import commands
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import Song,SongList
from maj.vpnrotator import VpnRotator
from maj.utils import botreplys

bot_status = {'hasGreeted': False, 'isIdentifying': False, 'triggerCount': 0}
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
        ws = bot._ws  # this is only needed to send messages within event_ready
        await ws.send_privmsg(config['channel'], "{0} Type '!track' to identify the current song playing.".format(botreplys.get_greeting(datetime.datetime.today())))
        bot_status['hasGreeted'] = True

@bot.event
async def event_message(ctx):
    'Runs every time a message is sent in chat.'

    # make sure the bot ignores itself and the streamer
    if ctx.author.name.lower() == config['botUsername'].lower():
        return

    await bot.handle_commands(ctx)
    # to send message within event_message: # await ctx.channel.send(ctx.content) # 

@bot.command(name='track', aliases=['playing', 'tune'])
async def track(ctx):
    global config
    global bot_status

    if bot_status['isIdentifying'] is True or twitch_recorder.is_recording or music_identifier.is_identifying:
        print('already trying to identify!')
        bot_status['triggerCount'] += 1

        if bot_status['triggerCount'] >= 5:
            bot_status['triggerCount'] = 0 # reset count so message sent every 5 times someone sends '!track' 
            await ctx.send(botreplys.get_already_listening_reply())

        return

    if len(playlist.songs) > 0:
        elapsedTime = datetime.datetime.now() - playlist.songs[-1].last_timestamp
        if elapsedTime.total_seconds() < 60:
            print("already identified a song less than 60 seconds ago ...")
            await ctx.send(playlist.get_last_song_msg())
            return

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
        print("no file recorded")
        bot_status['isIdentifying'] = False
        await ctx.send(botreplys.get_trouble_listening_reply())
        return

    try:
        response = music_identifier.identify(file_path)
        info = music_identifier.get_song_info_from_response(response)
    except Exception as e:
        print(e)
        music_identifier.is_identifying = False
        info = None

    if info is None:
        print("could not identify")
        bot_status['isIdentifying'] = False

        msg = botreplys.get_trouble_listening_reply() if twitch_recorder.is_blocked else botreplys.get_unknown_song_reply()
        await ctx.send(msg)
        return
        
    song = Song(info)
    playlist.add(song)
    msg = ""
    if info['multipleResults'] is True:
        msg += "(I think) "
    msg += f"Currently playing: {song.title} ║ Artist(s): {', '.join(song.artists)}  ║ Album: {song.album}"
    
    print(msg)
    bot_status['isIdentifying'] = False
    await ctx.send(msg)


@bot.command(name='majhelp', aliases=['bothelp'])
async def majhelp(ctx):
    await ctx.send('Type "!track" to identify the current song playing. "!last" for last song identified. "!setlist" to get all songs identified so far.')

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
        await ctx.send(playlist.get_last_song_msg())
    else:
        messages = []
        msg_reply = f"The last {num_tracks} tracks played (most recent first) --> "
        for i in range(1, num_tracks + 1):
            song_info = playlist.songs[-i].formatted_str(include_timestamp = False)
            if len(msg_reply + song_info) >= 500:
                messages.append(msg_reply)
                msg_reply = ""
            
            msg_reply += song_info + ' ██   '
        messages.append(msg_reply)

        print(messages)
        await send_message_batch(ctx, messages)


@bot.command(name='setlist')
async def setlist(ctx):
    msg = "(Title | Artists | Album) --> "
    messages = []
    for song in playlist.songs:
        if len(msg + song.formatted_str(include_timestamp=False)) >= 500:
            messages.append(msg)
            msg = ""
        
        msg += song.formatted_str(include_timestamp=False) + ' ██   '
    
    messages.append(msg)

    print(messages)
    await send_message_batch(ctx, messages)


async def send_message_batch(ctx, messages):
    for m in messages:
        await ctx.send(m)
        await asyncio.sleep(1.5 + random.random())


if __name__ == "__main__":
    print(botreplys.get_greeting(datetime.datetime.today()))

    token_updated = twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])

    # save new oauth token if fetched new one
    if token_updated:
        with open('config.json', 'w') as f:
            f.write(json.dumps(config, indent = 4))

    if twitch_recorder.check_user() is not None:
        bot.run()

    if vpn.is_connected:
        vpn.disconnect()
