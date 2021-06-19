import datetime
import os
import json
import csv


class Song:
    def __init__(self, info):
        self.title = info['title']
        self.album = info['album']
        self.artists = info['artists']
        self.last_timestamp = datetime.datetime.now()

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
        return {'title': self.title, 'album': self.album, 'artists': self.artists, 'timestamp': self.timestamp.isoformat(), 'last_timestamp': self.last_timestamp.isoformat()}

    def formatted_str(self, include_timestamp=True):
        if '.' in self.title:
            msg = '"{0}" ║ '.format(self.title)
        else:
            msg = "{0} ║ ".format(self.title)

        if len(self.artists) > 1:
            msg += "{0}".format(', '.join(self.artists))
        else:
            msg += "{0}".format(self.artists[0])

        if include_timestamp:
            msg += " ║ {0} ║ timestamp: {1}".format(
                self.album, self.timestamp.strftime('%H:%M:%S'))
        else:
            msg += " ║ {0}".format(self.album)

        return msg

    def get_last_identified_in_minutes(self):
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
        self.setlist_date = date_of_list
        self.save_path = save_path + '\\setlists\\' + channel
        self.full_path = self.save_path + '\\' + self.setlist_date.strftime('%Y-%m-%d.json')

        self.init_dir()
        self.load_from_file()

    def __str__(self):
        return str(self.json())

    def json(self):
        return {'songs': [s.json() for s in self.songs]}

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
            f.write(json.dumps(self.json(), indent=4))

    def add(self, song):
        for s in self.songs:
            if s.title == song.title and s.artists == song.artists:
                s.last_timestamp = song.last_timestamp
                self.save_to_file()
                return  # already added so just update last identified date 

        self.songs.append(song)
        self.save_to_file()

    def get_songs_str(self):
        return "; ".join([s.formatted_str() for s in self.songs])

    def get_last_song_msg(self):
        if len(self.songs) > 0:
            msg = f"The last track was identified {self.songs[-1].get_last_identified_in_minutes()}"
            msg += " --> {0}".format(
                self.songs[-1].formatted_str(include_timestamp=False))
            return msg

        return ""

    def save_setlist_csv(self, file_prefix="setlist"):
        setlist_start = datetime.datetime(self.setlist_date.year, self.setlist_date.month, self.setlist_date.day, 14, 0) # 2 pm PST

        table = [[str(s.timestamp - setlist_start).split(".")[0], s.title,
                "; ".join(s.artists), s.album] for s in self.songs]

        csv_path = self.save_path + '\\' + file_prefix + self.setlist_date.strftime('_%Y-%m-%d.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            
            # using csv.writer method from CSV package
            write = csv.writer(f)
            
            write.writerow(["Timestamp", "Title", "Artist", "Album"])
            write.writerows(table)

    def get_name_by_day(self, weekday):
        names = ["Jazz Club Monday","","Soulful Wednesday","","Disco Friday"]
        if weekday < 0 or weekday >= len(names):
            return ""
        return names[weekday]


def demo_usage():
    s = SongList("F:\\twitch", "misc", datetime.datetime.today())
    print(s.get_last_song_msg())
    print(s.get_songs_str())
    print('---')
    s.add(Song({'title': 'a', 'artists': ['1', '2'], 'album': 'z'}))
    s.add(Song({'title': 'a', 'artists': ['1', '2'], 'album': 'z'}))
    s.add(Song({'title': 'b', 'artists': ['3'], 'album': 'x'}))
    s.add(Song({'title': 'c', 'artists': ['4'], 'album': 'y'}))
    print(s.get_songs_str())


def print_setlist_tabular():
    from tabulate import tabulate
    setlist = SongList("F:\\twitch", "myanalogjournal_",
                       datetime.datetime.today())
    setlist_start = datetime.datetime(2021,6,18,14,0) # 2 pm PST

    table = [[str(s.timestamp - setlist_start).split(".")[0], s.title,
              "; ".join(s.artists), s.album] for s in setlist.songs]
    print(setlist.get_name_by_day(setlist_start.weekday))
    print(tabulate(table, headers=["Timestamp", "Title", "Artist", "Album"]))


def demo_csv_save():
    setlist = SongList("F:\\twitch", "myanalogjournal_",
                       datetime.datetime.today())
    setlist.save_setlist_csv()


# print_setlist_csv()
# demo_usage()
# demo_csv_save()
# print_setlist_tabular()