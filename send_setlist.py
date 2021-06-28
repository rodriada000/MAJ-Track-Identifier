import datetime
import json
import asyncio
from maj.songlist import Song,SongList
from maj.discordbot import MajBotClient
from maj.utils.spotifyclient import SpotifyClient


config = {}

with open('config.json', 'r') as f:
    config = json.load(f)



if __name__ == "__main__":

    loop = asyncio.get_event_loop()        
    playlist = SongList(config['recordedSavePath'], config['channel'], datetime.datetime.today())

    day_of_week = playlist.setlist_date.weekday()
    spotify_playlist = None

    # save setlist to a spotify playlist
    if config.get('spotify') is not None:
        spotify_client = SpotifyClient(config['spotify']['clientID'], config['spotify']['clientSecret'], scopes="playlist-read-collaborative playlist-modify-public playlist-modify-private playlist-read-private")
        
        prefix = f"MAJ {playlist.get_name_by_day(day_of_week)} Setlist"

        print('generating spotify playlist ...')
        spotify_playlist = spotify_client.create_setlist_playlist(playlist, name_prefix=prefix)
        print(spotify_playlist)

    # post spotify playlist and image of playlist to discord
    if config.get('discord') is not None:

        print('generating png ...')
        png_filename = 'setlist.png'
        playlist.save_setlist_png(output_path=png_filename)

        msg_content = f'{playlist.get_name_by_day(day_of_week)} {playlist.setlist_date.strftime("%Y-%m-%d")}'

        if spotify_playlist is not None:
            msg_content += ": " + spotify_playlist['external_urls']['spotify']

        discord_bot = MajBotClient(token=config['discord']['botToken'], guildName=config['discord']['guildName'], channelName=config['discord']['channelName'])

        print('sending discord message ...')
        print(msg_content)
        loop.run_until_complete(discord_bot.send_message(msg_content, png_filename))

        try:
            loop.run_until_complete(discord_bot.close())
        except Exception as e:
            pass 