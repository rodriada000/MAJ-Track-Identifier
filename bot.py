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

HAS_GREETED = False
GREETINGS = ["/me has landed!", "/me is in the house!", "a wild /me has appeared.", "yo yo yo it's your favorite bot bud !", "It's your friendly neighborhood bot bud /me !"]
DISCO_GREETINGS = ["/me would like to welcome you to Disco Friday!", "Who's ready for Disco Friday?! this bot is ready!", "/me is ready to shake it for Disco Friday!", "/me learned how to spell D-I-S-C-O F-R-I-D-A-Y !"]
JAZZ_GREETINGS = ["/me would like to welcome you to Monday Jazz Club!", "Who's ready for a relaxing Monday Jazz Club? this bot is.", "/me is ready to take it easy for Monday Jazz Club..."]
SOUL_GREETINGS = ["/me would like to welcome you to Soulful Wednesday!", "Who's ready for Soulful Wednesday?! this bot is ready!", "/me is ready to get soulful for Soulful Wednesday!", "choo choo all aboard the soul train for this Soulful Wednesday!"]

def get_greeting(date):
    if date.weekday() == 0:
        return JAZZ_GREETINGS[random.randint(0,len(JAZZ_GREETINGS) - 1)]
    elif date.weekday() == 2:
        return SOUL_GREETINGS[random.randint(0,len(SOUL_GREETINGS) - 1)]
    elif date.weekday() == 4:
        return DISCO_GREETINGS[random.randint(0,len(DISCO_GREETINGS) - 1)]
    else:
        return GREETINGS[random.randint(0,len(GREETINGS) - 1)]

config = {}


with open('config.json', 'r') as f:
    config = json.load(f)

config['isRunning'] = False

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
token_updated = twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])

# save new oauth token if fetched new one
if token_updated:
    with open('config.json', 'w') as f:
        f.write(json.dumps(config, indent = 4))

# set up music identifier
music_identifier = Identifier(config['acrKey'], config['acrSecret'], config['acrHostUrl'])


@bot.event
async def event_ready():
    'Called once when the bot goes online.'
    global HAS_GREETED

    print(f"{config['botUsername']} is online!")
    if HAS_GREETED is False:
        ws = bot._ws  # this is only needed to send messages within event_ready
        await ws.send_privmsg(config['channel'], "{0} Type '!track' to identify the current song playing.".format(get_greeting(datetime.datetime.today())))
        HAS_GREETED = True

@bot.event
async def event_message(ctx):
    'Runs every time a message is sent in chat.'

    # make sure the bot ignores itself and the streamer
    if ctx.author.name.lower() == config['botUsername'].lower():
        return

    await bot.handle_commands(ctx)
    # await ctx.channel.send(ctx.content) # to send message within event_message



@bot.command(name='majhelp', aliases=['bothelp'])
async def majhelp(ctx):
    await ctx.send('Type "!track" to identify the current song playing. "!last" for last song identified. "!setlist" to get all songs identified so far.')

@bot.command(name='track', aliases=['playing', 'tune'])
async def track(ctx):
    global config

    if config['isRunning'] is True or twitch_recorder.is_recording or music_identifier.is_identifying:
        print('already trying to identify!')
        return

    if len(playlist.songs) > 0:
        elapsedTime = datetime.datetime.now() - playlist.songs[-1].timestamp
        if elapsedTime.total_seconds() < 90:
            print("already identified a song less than 90 seconds ago ...")
            await ctx.send(get_last_track_msg())
            return

    config['isRunning'] = True

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
        file_path = None

    if file_path is not None:
        try:
            response = music_identifier.identify(file_path)
            info = music_identifier.get_song_info_from_response(response)
        except Exception as e:
            print(e)
            info = None

        if info is not None:
            playlist.add(Song(info))
            msg = ""
            if info['multipleResults'] is True:
                msg += "(I think) "
            msg += "Currently playing: " + info['title'] + ' || Artist(s): ' + ', '.join(info['artists']) + ' || Album: ' + info['album']
            print(msg)
            await ctx.send(msg)
        else:
            msg = ""
            if twitch_recorder.is_blocked:
                msg = "I had trouble listening. Please try again ..."
            else:
                msg = "I can't tell what's playing..."
                
            await ctx.send(msg)
            print("could not identify")
    else:
        print("no file recorded")

    config['isRunning'] = False

@bot.command(name="lastsong", aliases=["last"])
async def lastsong(ctx):

    if len(playlist.songs) > 0:
        await ctx.send(get_last_track_msg())

def get_last_track_msg():
    if len(playlist.songs) > 0:
        elapsedTime = datetime.datetime.now() - playlist.songs[-1].timestamp
        mins,sec = divmod(elapsedTime.total_seconds(), 60)

        msg = "The last track was identified "
        if mins > 1:
            msg += "{0} minutes ago".format(round(mins,0))
        else:
            msg += "{0} seconds ago".format(round(sec,0))

        msg += " - {0}".format(playlist.songs[-1].formatted_str(include_timestamp=False))
        return msg
    return ""


@bot.command(name='setlist')
async def setlist(ctx):
    msg = "(Title | Artists | Album) --> "
    messages = []
    for song in playlist.songs:
        if len(msg + song.formatted_str(include_timestamp=False)) >= 500:
            messages.append(msg)
            msg = ""
        
        msg += song.formatted_str(include_timestamp=False) + ';-- '
    
    messages.append(msg)

    print(messages)

    for m in messages:
        await ctx.send(m)
        await asyncio.sleep(1.5 + random.random())

if __name__ == "__main__":
    print(get_greeting(datetime.datetime.today()))

    if twitch_recorder.check_user() is not None:
        bot.run()

    if vpn.is_connected:
        vpn.disconnect()