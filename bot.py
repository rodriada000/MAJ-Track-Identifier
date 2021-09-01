import datetime
import json
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sys import stdout
from time import sleep
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import SongList
from maj.vpnrotator import VpnRotator
from maj.pollvote import MajPoll
from maj.twitchbot import TwitchBot
from maj.utils.botreplys import load_chat_intents, get_reply_based_on_message

DEFAULT_FMT = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"

config = {}

with open('config.json', 'r') as f:
    config = json.load(f)

logFormatter = logging.Formatter(config.get("loggingFormat", DEFAULT_FMT))
logger = logging.getLogger()
logger.setLevel(config.get("loggingLevel", logging.INFO))


fileHandler = RotatingFileHandler('bot.log', mode='a', maxBytes=5*1024*1024, backupCount=1, encoding='utf-8', delay=0)
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# setup vpn rotator to connect to different vpns when twitch recording is blocked
vpn = VpnRotator(config['vpnConfigFolders'], config['vpnUserPwdConfigPath'])

# set up list to cache songs (will load from file if exists)
playlist = SongList(config['recordedSavePath'], config['channel'], datetime.datetime.today())

# set up recorder
twitch_recorder = TwitchRecorder(config['botClientID'], config['botSecret'], config['channel'], config['recordedSavePath'])

# set up music identifier
music_identifier = Identifier(config['acrKey'], config['acrSecret'], config['acrHostUrl'])

bot = None

async def identify_on_interval():
    if bot.is_identifying:
        return

    while True:
        await bot.try_identify()
        logger.info('cooling down until next check ...')
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
        indentify_task = None

        # auto-id can be turned off if cooldown is < 0 
        if config.get("identifyCooldown", 30) > 0:
            indentify_task = asyncio.create_task(identify_on_interval())

        try:
            logger.info('waiting for channel to be offline ...')
            while bot.twitch_recorder.is_user_online() or config.get('enabledOffline', False):
                await asyncio.sleep(900)
        except Exception:
            pass

        logger.info("channel offline. closing down ...")

        await bot.send_channel_message(get_reply_based_on_message("bye", "everyone", bot.playlist.setlist_start))

        running_task.cancel()

        if indentify_task is not None:
            indentify_task.cancel()

        try:
            await running_task
        except asyncio.CancelledError:
            logger.info("canceled bot task")

    except Exception as e:
        logger.error(f"run_bot error: {e}")
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
        logger.info('twitch oauth token update ...')
        config['botToken']['oauthToken'] = twitch_recorder.oauth_token
        config['botToken']['expirationDate'] = twitch_recorder.expiration_date.strftime("%Y-%m-%d")
        with open('config.json', 'w') as f:
            f.write(json.dumps(config, indent = 4))

    try:
        while not twitch_recorder.is_user_online() and not config.get('enabledOffline', False):
            logger.info('waiting for channel to be online ...')
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"error while waiting: {e}")

    # update the datetime to match when user goes online
    if not playlist.has_started:
        playlist.setlist_start = datetime.datetime.today()
        playlist.has_started = True

    # have twitch bot run in another task
    try:
        bot_task = asyncio.create_task(run_bot())
        await bot_task
    except Exception as e:
        logger.warning(f"bot_task ex thrown: {e}")

    if vpn is not None and vpn.is_connected:
        logger.info("vpn disconnected ...")
        vpn.disconnect()
    
    logger.info("end of main.")
 

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(shutdown(loop))
        loop.close()
        logger.info("Successfully shutdown ...")
