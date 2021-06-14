import datetime
import os
import json

class Song:
    def __init__(self, info):
        self.title = info['title']
        self.album = info['album']
        self.artists = info['artists']

        if info.get('timestamp', None) is None:
            self.timestamp = datetime.datetime.now()
        else:
            self.timestamp = datetime.datetime.fromisoformat(info['timestamp'])

    def formatted_str(self, include_timestamp=True):
        msg = "({0} | ".format(self.title)
        if len(self.artists) > 1:
            msg += "{0}".format(', '.join(self.artists))
        else:
            msg += "{0}".format(self.artists[0])
        
        if include_timestamp:
            msg += " | {0} | timestamp: {1})".format(self.album, self.timestamp.strftime('%H:%M:%S'))
        else:
            msg += " | {0})".format(self.album)

        return msg

    def json(self):
        return { 'title': self.title, 'album': self.album, 'artists': self.artists, 'timestamp': self.timestamp.isoformat()}


class SongList:
    def __init__(self, save_path, channel, date_of_list):
        self.songs = []
        self.save_path =  save_path + '\\setlists\\' + channel
        self.full_path = self.save_path + '\\'  + date_of_list.strftime('%Y-%m-%d.json')
        
        self.init_dir()
        self.load_from_file()

    def init_dir(self):
        # create directory for setlists if not exist
        if os.path.isdir(self.save_path) is False:
            os.makedirs(self.save_path)

    def load_from_file(self):
        if os.path.exists(self.full_path):
            with open(self.full_path, 'r') as f:
                saved = json.load(f)
                self.songs = [Song(s) for s in saved['songs']]

    def save_to_file(self):
        with open(self.full_path, "w") as f:
            f.write(json.dumps(self.json(), indent = 4))

    def add(self, song):
        for s in self.songs:
            if s.title == song.title and s.artists == song.artists:
                return # already added

        self.songs.append(song)
        self.save_to_file()

    def get_songs_str(self):
        return "; ".join([s.formatted_str() for s in self.songs])

    def json(self):
        return {'songs': [s.json() for s in self.songs]}


def demo_usage():
    s = SongList("F:\\twitch", "misc", datetime.datetime.today())
    print(s.get_songs_str())
    print('---')
    s.add(Song({'title': 'a', 'artists': ['1', '2'], 'album': 'z'}))
    s.add(Song({'title': 'a', 'artists': ['1', '2'], 'album': 'z'}))
    s.add(Song({'title': 'b', 'artists': ['3'], 'album': 'x'}))
    s.add(Song({'title': 'c', 'artists': ['4'], 'album': 'y'}))
    print(s.get_songs_str())
    print(s.json())

def print_setlist_tabular():
    from tabulate import tabulate
    setlist = SongList("F:\\twitch", "myanalogjournal_", datetime.datetime.today())
    setlist_start = datetime.datetime(2021, 6,14,14,0) # 2 pm PST

    table = [[str(s.timestamp - setlist_start).split(".")[0],s.title,"; ".join(s.artists),s.album] for s in setlist.songs]
    print(tabulate(table, headers=["Timestamp","Title", "Artist", "Album"]))

def print_setlist_csv():
    from tabulate import tabulate
    setlist = SongList("F:\\twitch", "myanalogjournal_", datetime.datetime.today())
    setlist_start = datetime.datetime(2021, 6,14,14,0) # 2 pm PST

    table = [[str(s.timestamp - setlist_start).split(".")[0],s.title,"; ".join(s.artists),s.album] for s in setlist.songs]
    print("Timestamp,Title,Artist,Album")
    for row in table:
        print('{0},"{1}","{2}","{3}"'.format(row[0], row[1], row[2], row[3]))


# print_setlist_csv()