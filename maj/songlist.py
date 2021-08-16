import datetime
import os
import json
import csv
import string
import imgkit
from tabulate import tabulate
from maj.utils.botreplys import get_stream_name_by_day

class Song:
    def __init__(self, info):
        self.title = info['title']
        self.album = info['album']
        self.artists = info['artists']
        self.duration_s = info.get('duration_s', 0)
        self.last_timestamp = datetime.datetime.now()
        self.added_by = info.get('added_by', '')

        if info.get('last_timestamp', None) is None:
            self.last_timestamp = datetime.datetime.now()
        else:
            self.last_timestamp = datetime.datetime.fromisoformat(info['last_timestamp'])

        # timestamp is datetime of first identification of the song
        if info.get('timestamp', None) is None:
            self.timestamp = datetime.datetime.now()
        else:
            self.timestamp = datetime.datetime.fromisoformat(info['timestamp'])

    def __str__(self):
        return str(self.json())

    def json(self):
        return {'title': self.title,
                'album': self.album,
                'artists': self.artists,
                'duration_s': self.duration_s,
                'timestamp': self.timestamp.isoformat(),
                'last_timestamp': self.last_timestamp.isoformat(),
                'added_by': self.added_by}

    def get_current_playing_msg(self):
        return f'Currently playing: "{self.title}" ║ Artist(s): {", ".join(self.artists)}  ║ Album: {self.album}'

    def formatted_str(self, include_timestamp=False):
        if '.' in self.title:
            msg = '"{0}" ║ '.format(self.title)
        else:
            msg = "{0} ║ ".format(self.title)

        if len(self.artists) > 1:
            msg += "{0}".format(', '.join(self.artists))
        else:
            msg += "{0}".format(self.artists[0])

        if self.album != "":
            msg += " ║ {0}".format(self.album)

        if include_timestamp:
            msg += " ║ timestamp: {0}".format(self.timestamp.strftime('%H:%M:%S'))

        return msg

    def get_last_identified_in_seconds(self):
        elapsedTime = datetime.datetime.now() - self.last_timestamp
        return elapsedTime.total_seconds()

    def get_last_identified_str(self):
        elapsedTime = datetime.datetime.now() - self.last_timestamp
        mins, sec = divmod(elapsedTime.total_seconds(), 60)

        if mins > 1:
            return "{0} minutes ago".format(round(mins, 0))
        else:
            return "{0} seconds ago".format(round(sec, 0))
        return ""



class SongList:
    def __init__(self, save_path, channel, date_of_list):
        self.songs = []
        self.setlist_start = date_of_list
        self.has_started = False
        self.save_path = save_path + '\\setlists\\' + channel
        self.full_path = self.save_path + '\\' + self.setlist_start.strftime('%Y-%m-%d.json')

        self.init_dir()
        self.load_from_file()

    def __str__(self):
        return str(self.json())

    def json(self):
        return {'setlist_start': self.setlist_start.isoformat(),
                'has_started': self.has_started,
                'songs': [s.json() for s in self.songs]}

    def init_dir(self):
        # create directory for setlists if not exist
        if os.path.isdir(self.save_path) is False:
            os.makedirs(self.save_path)

    def load_from_file(self):
        if os.path.exists(self.full_path):
            with open(self.full_path, 'r') as f:
                saved = json.load(f)
                self.songs = [Song(s) for s in saved['songs']]
                self.songs.sort(key=lambda x: x.timestamp)
                self.has_started = saved.get('has_started', False)
                if saved.get('setlist_start', None) is not None:
                    self.setlist_start = datetime.datetime.fromisoformat(saved['setlist_start'])

    def save_to_file(self):
        with open(self.full_path, "w") as f:
            f.write(json.dumps(self.json(), indent=4))

    def add(self, song):
        to_add_title = song.title.lower().translate(str.maketrans('', '', string.punctuation))

        for s in self.songs:
            title_lower = s.title.lower().translate(str.maketrans('', '', string.punctuation))
            if title_lower == to_add_title and s.artists == song.artists:
                s.last_timestamp = song.last_timestamp
                self.save_to_file()
                return False  # already added so just update last identified date 

        self.songs.append(song)
        self.save_to_file()
        return True

    def get_last_song_msg(self):
        if len(self.songs) > 0:
            last_song = self.songs[-1]
            if last_song.get_last_identified_in_seconds() <= 30:
                return last_song.get_current_playing_msg()

            msg = f"The last track was identified {last_song.get_last_identified_str()}"
            msg += " --> {0}".format(
                last_song.formatted_str())
            return msg

        return ""

    def save_setlist_csv(self, file_prefix="setlist"):

        table = self.get_songs_tabular()
        csv_path = self.save_path + '\\' + file_prefix + self.setlist_start.strftime('_%Y-%m-%d.csv')

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            write = csv.writer(f)
            
            write.writerow(["Timestamp", "Title", "Artist", "Album"])
            write.writerows(table)

        return csv_path

    def save_setlist_png(self, output_path='setlist.png'):

        table = self.get_songs_tabular()
        html_path = output_path.replace(".png", ".html")

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(f"<html><head>{get_stream_name_by_day(self.setlist_start.weekday())} {self.setlist_start.strftime('%Y-%m-%d')}</head><body>")
            f.write(tabulate(table, headers=["Timestamp", "Title", "Artist", "Album"], tablefmt='html'))
            f.write("</body></html>")

        options = {
            'format': 'png',
            'encoding': "UTF-8"
        }
        imgkit.from_file(html_path, output_path, options=options)

    def get_songs_tabular(self):
        return [[str(s.timestamp - self.setlist_start).split(".")[0], s.title, "; ".join(s.artists), s.album] for s in self.songs]




def demo_usage():
    today = datetime.datetime.today()
    s = SongList("F:\\twitch", "misc", today)
    print(get_stream_name_by_day(today.weekday()))
    print(s.get_last_song_msg())
    print('---')
    s.add(Song({'title': 'a', 'artists': ['1', '2'], 'album': 'z'}))
    s.add(Song({'title': 'a', 'artists': ['1', '2'], 'album': 'z'}))
    s.add(Song({'title': 'b', 'artists': ['3'], 'album': 'x'}))
    s.add(Song({'title': 'c', 'artists': ['4'], 'album': 'y'}))
    p = s.save_setlist_csv('testlist')
    print(s.get_songs_tabular())
    print(p)
    print(str(s))

def print_setlist_tabular():
    today = datetime.date.today()
    setlist = SongList("F:\\twitch", "myanalogjournal_",
                       today)

    table = setlist.get_songs_tabular()
    print(get_stream_name_by_day(today.weekday()))
    print(tabulate(table, headers=["Timestamp", "Title", "Artist", "Album"]))


def demo_csv_save():
    setlist = SongList("F:\\twitch", "myanalogjournal_",
                       datetime.datetime(2021,6,23))
    p = setlist.save_setlist_csv()
    print(p)

def demo_png_save():
    setlist = SongList("F:\\twitch", "myanalogjournal_",
                       datetime.datetime(2021,6,23))
    setlist.save_setlist_png()



# if __name__ == "__main__":
#     demo_usage()
#     today = datetime.datetime(2021,6,30,14,0)
#     s = SongList("F:\\twitch", "myanalogjournal_", today)
#     print(s.get_last_song_msg())
#     print('---')
#     print(s.get_songs_tabular())
    # demo_png_save()
    # demo_usage()
    # demo_csv_save()
