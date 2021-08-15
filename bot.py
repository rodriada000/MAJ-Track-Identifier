import datetime
import json
import asyncio
from time import sleep
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import SongList
from maj.vpnrotator import VpnRotator
from maj.pollvote import MajPoll
from maj.twitchbot import TwitchBot
from maj.utils.botreplys import load_chat_intents, get_reply_based_on_message

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

bot = None

async def try_indentify():
    if bot.is_identifying:
        return


    while True:
        await bot.try_identify()
        print('cooling down until next check ...')
        await asyncio.sleep(config.get("identifyCooldown", 30))

async def run_bot():
    global bot
    try:
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

        running_task = asyncio.create_task(bot.start())
        indentify_task = asyncio.create_task(try_indentify())

        try:
            print('waiting for channel to be offline ...')
            while bot.twitch_recorder.check_user() is not None or config.get('enabledOffline', False):
                await asyncio.sleep(60)
        except Exception:
            pass

        print("channel offline. closing down ...")

        await bot.send_channel_message(get_reply_based_on_message("bye", "everyone", bot.playlist.setlist_start))

        running_task.cancel()
        indentify_task.cancel()
        try:
            await running_task
        except asyncio.CancelledError:
            print("canceled bot task")

    except Exception as e:
        print(f"run_bot error: {e}")
        pass

async def shutdown(loop):
    """Cancel all tasks still running."""
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]

    [task.cancel() for task in tasks]

    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    load_chat_intents('./maj/utils/intents.json')

    token_updated = twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])    

    # save new oauth token if fetched new one
    if token_updated:
        config['botToken']['oauthToken'] = twitch_recorder.oauth_token
        config['botToken']['expirationDate'] = twitch_recorder.expiration_date.strftime("%Y-%m-%d")
        with open('config.json', 'w') as f:
            f.write(json.dumps(config, indent = 4))

    try:
        while twitch_recorder.check_user() is None and not config.get('enabledOffline', False):
            print('waiting for channel to be online ...')
            await asyncio.sleep(60)
    except Exception as e:
        print(f"error while waiting: {e}")

    # update the datetime to match when user goes online
    if not playlist.has_started:
        playlist.setlist_start = datetime.datetime.today()
        playlist.has_started = True

    # have twitch bot run in another task
    try:
        bot_task = asyncio.create_task(run_bot())
        await bot_task
    except Exception as e:
        print(f"bot_task ex thrown: {e}")

    if vpn is not None and vpn.is_connected:
        print("vpn disconnected ...")
        vpn.disconnect()
    
    print("end of main.")
 

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(shutdown(loop))
        loop.close()
        print("Successfully shutdown ...")
