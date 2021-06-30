import datetime
import json
import asyncio
from os import path
from maj.songlist import Song,SongList
from maj.discordbot import MajBotClient
from maj.utils.spotifyclient import SpotifyClient
from maj.utils.botreplys import get_stream_name_by_day


config = {}

with open('config.json', 'r') as f:
    config = json.load(f)



if __name__ == "__main__":

    loop = asyncio.get_event_loop()        
    playlist = SongList(config['recordedSavePath'], config['channel'], datetime.datetime.today())

    day_of_week = playlist.setlist_date.weekday()
    spotify_playlist = None
    tracks_added = 0

    # save setlist to a spotify playlist
    if config.get('spotify') is not None:
        spotify_client = SpotifyClient(config['spotify']['clientID'], config['spotify']['clientSecret'], scopes="playlist-read-collaborative playlist-modify-public playlist-modify-private playlist-read-private")
        
        prefix = f"MAJ {get_stream_name_by_day(day_of_week)} Setlist"

        print('generating spotify playlist ...')
        spotify_playlist, tracks_added = spotify_client.create_setlist_playlist(playlist, name_prefix=prefix, is_public=False, is_collab=True, verbose=True)
        print(spotify_playlist)

    # post spotify playlist and image of playlist to discord
    if config.get('discord') is not None:

        print('generating png ...')
        png_filename = 'setlist.png'
        playlist.save_setlist_png(output_path=png_filename)

        print('generating csv ...')
        path_to_csv = playlist.save_setlist_csv()

        msg_content = f'{get_stream_name_by_day(day_of_week)} {playlist.setlist_date.strftime("%Y-%m-%d")}'
        
        if spotify_playlist is not None:
            msg_content += f": {spotify_playlist['external_urls']['spotify']} \n...Found {tracks_added} of {len(playlist.songs)} songs on Spotify."

        discord_bot = MajBotClient(token=config['discord']['botToken'], guildName=config['discord']['guildName'], channelName=config['discord']['channelName'])

        print('sending discord message ...')
        print(msg_content)
        loop.run_until_complete(discord_bot.send_message(msg_content, png_filename))
        loop.run_until_complete(discord_bot.send_message("", path_to_csv, path.basename(path_to_csv)))

        try:
            loop.run_until_complete(discord_bot.close())
        except Exception as e:
            pass 