import datetime
import json
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sys import stdout
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import SongList
from maj.vpnrotator import VpnRotator
from maj.twitchbot import TwitchBot
from maj.utils.botreplys import load_chat_intents, get_reply_based_on_message

config = {}

with open('config.json', 'r') as f:
    config = json.load(f)

# setup logging
DEFAULT_FMT = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"

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
    while True:
        if bot is None or bot.is_identifying:
            continue

        try:
            await bot.try_identify()
            logger.info('cooling down until next check ...')
            await asyncio.sleep(config.get("identifyCooldown", 30))
        except Exception as e:
            logger.error(f"identify_on_interval error: {e}")

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

        offline_time = None
        last_checked = datetime.datetime.today()

        logger.info('waiting for channel to be offline ...')
        while True:
            try:
                # check twitch channel online status every 15 minutes
                last_checked_seconds = (datetime.datetime.now() - last_checked).total_seconds()
                if last_checked_seconds > 600:
                    last_checked = datetime.datetime.today()
                    if not bot.twitch_recorder.is_user_online() and offline_time is None:
                        logger.warning("twitch channel appears offline")
                        offline_time = datetime.datetime.today()
                    elif bot.twitch_recorder.is_user_online():
                        offline_time = None

                    if offline_time is not None:
                        offline_in_seconds = (datetime.datetime.now() - offline_time).total_seconds()

                        if offline_in_seconds > config.get('shutDownAfterSeconds', 120) and not config.get('enabledOffline', False):
                            break

                # restart async tasks if an exception occurred
                if running_task.done() and running_task.exception() is not None:
                    logger.warn(f'running_task exited with exception... restarting: {running_task.exception()}')
                    await running_task
                    running_task = asyncio.create_task(bot.start())

                if indentify_task is not None and indentify_task.done() and indentify_task.exception() is not None:
                    logger.warn(f'indentify_task exited with exception... restarting: {indentify_task.exception()}')
                    await indentify_task
                    indentify_task = asyncio.create_task(identify_on_interval())

                await asyncio.sleep(30)
            except Exception as e:
                print(e)
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

        # restart bot if an exception occurred
        if bot_task.done() and bot_task.exception() is not None:
            logger.warn(f'bot_task exited with exception... restarting: {bot_task.exception()}')
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
