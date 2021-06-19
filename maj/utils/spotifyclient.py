from spotipy import oauth2, Spotify
import json
import datetime
import time
from maj.songlist import SongList,Song


CACHE_PATH = ".cache"
IGNORE_WORDS = ["(Original Mix)", "(Remix)", "(REMIX)"]

class SpotifyClient:
    """
    class to capture main functions for spotify such as authorizing and refreshing tokens
    """

    def __init__(self, client_id="", secret="", scopes="", redirect_url="https://localhost:8080/callback"):
        self.oauth = oauth2.SpotifyOAuth(client_id=client_id,client_secret=secret,redirect_uri=redirect_url,scope=scopes, cache_path=CACHE_PATH)
        self.token_info = self.oauth.get_cached_token()
        if not self.token_info:
            self.set_token_info()

        self.get_access_token()
        self.sp = Spotify(auth=self.token)


    def set_token_info(self):
        print('no cached token found. Use web browser to get refresh/access token.')
        auth_url = self.oauth.get_authorize_url()
        print(auth_url)
        response = input('Paste the above link into your browser, then paste the redirect url here: ')

        code = self.oauth.parse_response_code(response)
        self.token_info = self.oauth.get_access_token(code)


    def get_access_token(self):
        if self.oauth.is_token_expired(self.token_info):
            print('access token is expired. refreshing ...')
            self.token_info = self.oauth.refresh_access_token(self.token_info['refresh_token'])

        self.token = self.token_info['access_token']

    def search_tracks(self, title=None, artist=None, album=None):
        query = ''

        if title is not None:
            for w in IGNORE_WORDS:
                title = title.replace(w, '')
            query += f'track:"{title}"+'
                
        if artist is not None:
            query += f'artist:"{artist}"+'

        if album is not None:
            query += f'album:"{album}"+'
                
        query = query[:-1]

        results = self.sp.search(query, limit=3, offset=0, type='track')

        if results['tracks'] is None or len(results['tracks']['items']) == 0:
            if artist is None:
                return None # nothing found
            
            # try searching with only title if artist was passed in
            results = self.sp.search(f'track:"{title}"', limit=3, offset=0, type='track')


        if results['tracks'] and len(results['tracks']['items']) > 0:
            track = results['tracks']['items'][0]

            print([t['artists'] for t in results['tracks']['items']])

            return {
                'id': track['id'],
                'uri': track['uri'],
                'name': track['name'],
                'albumName': track['album']['name'],    
                'artists': track['artists'],
                'externalUrl': track['external_urls']['spotify']
            }
        else:
            return None

    def create_playlist(self, name, description='', is_public=True, is_collab=False):
        return self.sp.user_playlist_create(self.get_user_id(), name, public=is_public, collaborative=is_collab, description=description)

    def add_track_to_playlist(self, playlist_id, track_id):
        return self.sp.user_playlist_add_tracks(self.get_user_id(), playlist_id, track_id)

    def get_user_id(self):
        if self.sp is not None and self.sp.current_user() is not None:
            return self.sp.current_user()['id']
        else:
            return None

    def create_setlist_playlist(self, setlist, name_prefix='MAJ Setlist', is_public=True, is_collab=False):
        playlist_name = f'{name_prefix} {setlist.setlist_date.strftime("%Y-%m-%d")}'
        tracks = []

        for song in setlist.songs:
            result = self.search_tracks(title=song.title, artist=song.artists[0]) # search by album too? search for each artist?
            if result is not None:
                tracks.append(result)
            time.sleep(1) # add a delay between each search so requests arent rapid

        if len(tracks) == 0:
            return # no songs found that can be added to a playlist

        playlist = self.create_playlist(playlist_name, "Automatically generated from python - MAJ Music bot", is_public, is_collab)
        self.add_track_to_playlist(playlist['id'], [t['id'] for t in tracks])

        return playlist



def demo_search_usage():
    config = {}

    with open('.\\config.json') as f:
        config = json.load(f)

    client = SpotifyClient(config['spotify']['clientID'], config['spotify']['clientSecret'], scopes="playlist-read-collaborative playlist-modify-public playlist-modify-private playlist-read-private")
    track = client.search_tracks(title="Try It Out", artist="Simon Dunmore")

    print(track)

def demo_create_from_setlist():
    config = {}

    setlist_start = datetime.datetime(2021,6,18,14,0) # 2 pm PST
    setlist = SongList("F:\\twitch", "myanalogjournal_", setlist_start)

    with open('.\\config.json') as f:
        config = json.load(f)

    client = SpotifyClient(config['spotify']['clientID'], config['spotify']['clientSecret'], scopes="playlist-read-collaborative playlist-modify-public playlist-modify-private playlist-read-private")
    playlist = client.create_setlist_playlist(setlist, name_prefix='MAJ Disco Friday Setlist')
    
    print(playlist)

# demo_search_usage()
# demo_create_from_setlist()