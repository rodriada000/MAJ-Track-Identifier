import datetime
import json
import asyncio
import logging
from sys import stdout
from os import path
from time import sleep
from maj.songlist import Song,SongList
from maj.discordbot import MajBotClient
from maj.twitchrecorder import TwitchRecorder
from maj.utils.spotifyclient import SpotifyClient
from maj.utils.botreplys import get_stream_name_by_day
from bot import logger, config

if __name__ == "__main__":

    loop = asyncio.get_event_loop()        

    spotify_playlist = None
    tracks_added = 0

    # ensure user has stopped streaming before generating/posting
    twitch_recorder = TwitchRecorder(config['botClientID'], config['botSecret'], config['channel'], config['recordedSavePath'])
    twitch_recorder.authorize(config['botToken']['oauthToken'], config['botToken']['expirationDate'])

    try:
        while twitch_recorder.is_user_online():
            logger.info('waiting for channel to be offline ...')
            sleep(60)
    except KeyboardInterrupt:
        pass

    playlist = SongList(config['recordedSavePath'], config['channel'], datetime.datetime.today())
    day_of_week = playlist.setlist_start.weekday()

    # save setlist to a spotify playlist
    if config.get('spotify') is not None and len(playlist.songs) > 0:
        spotify_client = SpotifyClient(config['spotify']['clientID'], config['spotify']['clientSecret'], scopes="playlist-read-collaborative playlist-modify-public playlist-modify-private playlist-read-private")
        
        prefix = f"MAJ {get_stream_name_by_day(day_of_week)} Setlist"

        logger.info('generating spotify playlist ...')
        spotify_playlist, tracks_added = spotify_client.create_setlist_playlist(playlist, name_prefix=prefix, is_public=False, is_collab=True, verbose=True)
        logger.info(spotify_playlist)

        megamixes = spotify_client.get_playlist_ids(f'MAJ {get_stream_name_by_day(day_of_week)} Megamix')
        if config['spotify'].get('enableMegamix', True) and len(megamixes) > 0:
            logger.info('adding to megamix ...')
            megamix_id = megamixes[0]
            spotify_client.merge_playlists(megamix_id, spotify_playlist['id'])

    # post spotify playlist and image of playlist to discord
    if config.get('discord') is not None and len(playlist.songs) > 0:

        logger.info('generating png ...')
        png_filename = 'setlist.png'
        playlist.save_setlist_png(output_path=png_filename)

        logger.info('generating csv ...')
        path_to_csv = playlist.save_setlist_csv()

        msg_content = f'{get_stream_name_by_day(day_of_week)} {playlist.setlist_start.strftime("%Y-%m-%d")}'
        
        if spotify_playlist is not None:
            msg_content += f": {spotify_playlist['external_urls']['spotify']} \n...Found {tracks_added} of {len(playlist.songs)} songs on Spotify."

        discord_bot = MajBotClient(token=config['discord']['botToken'], guildName=config['discord']['guildName'], channelName=config['discord']['channelName'])

        logger.info('sending discord message ...')
        logger.info(msg_content)
        loop.run_until_complete(discord_bot.send_message(msg_content, png_filename))
        loop.run_until_complete(discord_bot.send_message("", path_to_csv, path.basename(path_to_csv)))

        try:
            loop.run_until_complete(discord_bot.close())
        except Exception as e:
            pass 