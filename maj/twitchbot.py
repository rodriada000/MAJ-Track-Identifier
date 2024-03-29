import os
import pathlib
import datetime
import json
import asyncio
import random
import logging
from time import sleep
from twitchio.ext import commands
from twitchio.dataclasses import Message
from maj.identifier import Identifier
from maj.twitchrecorder import TwitchRecorder
from maj.songlist import Song, SongList
from maj.vpnrotator import VpnRotator
from maj.discordbot import MajBotClient
from maj.pollvote import MajPoll
from maj.utils import botreplys
from maj.utils.spotifyclient import SpotifyClient
from maj.utils.chatgpt import ChatGPTBot

log = logging.getLogger(__name__)


SEP_CHAR = ' ██   '

class TwitchBot(commands.Bot):
    def __init__(self, config, playlist, recorder, identifier, *args, **kwargs):
        super(TwitchBot, self).__init__(*args, **kwargs)
        self.config = config
        self.playlist = playlist
        self.twitch_recorder = recorder
        self.music_identifier = identifier
        self.vpn = kwargs.get("vpn", None)

        chatgpt_key = kwargs.get("chatgpt_key", None)
        self.chatgpt_bot = None

        if chatgpt_key is not None:
            self.chatgpt_bot = ChatGPTBot(chatgpt_key)

        self.maj_poll = None
        self.prev_polls = []
        self.has_greeted = False
        self.is_identifying = False
        self.is_silenced = True
        self.trigger_count = 0
        self.try_count = 0
        self.max_trys = 10

        self.last_msg = ""
        self.last_msg_sent = datetime.datetime.now()

    async def event_ready(self):
        """
        Called once when the bot goes online.
        """

        log.info(f"{self.config['botUsername']} is online!")
        if self.has_greeted is False:
            self.has_greeted = True

            if self.config['print_only'] is False:
                await self.send_channel_message("{0} Type '!track' to identify the current song playing.".format(botreplys.get_greeting(datetime.datetime.today())))

    async def event_message(self, message):
        """
        Runs every time a message is sent in chat.
        """

        # make sure the bot ignores itself
        if message.author.name.lower() == self.config['botUsername'].lower():
            return

        if botreplys.get_intent_tag(message.content) == "identify":
            ctx = await self.get_context(message)
            await self.send_lastsong_message(ctx, message.content) 
            
        elif self.is_bot_mentioned(message.content):
            ctx = await self.get_context(message)
            response = botreplys.get_reply_based_on_message(message.content, message.author.name, self.playlist.setlist_start)

            if response != "":
                await self.send_message(ctx, response)
            elif self.chatgpt_bot is not None:
                generated_resp = self.chatgpt_bot.complete_chat(message.content)
                if generated_resp != "":
                    await self.send_message(ctx, generated_resp)
            else:
                log.info(f'[unknownMention] {message.content}')

        await self.handle_commands(message)

    def is_bot_mentioned(self, message):
        return self.config['botUsername'].lower() in message.lower()

    @commands.command(name='track', aliases=['playing', 'tune', 'TRACK', 'thong', 'song'])
    async def track(self, ctx):

        self.trigger_count += 1
        if self.trigger_count >= 5:
            self.trigger_count = 0 # reset count so message sent every 5 times someone sends '!track' 
            await self.send_message(ctx, botreplys.get_already_listening_reply())

        if self.is_identifying:
            log.info('already trying to identify!')
            return

        if self.config.get("identifyCooldown", 30) > 0:
            # when auto-id is enabled then print song if recently identified (guessing it is currently playing)
            await self.send_currentplaying_message(ctx, ctx.content) 
            return
        
        # start identifying 
        if len(self.playlist.songs) > 0:
            elapsedTime = datetime.datetime.now() - self.playlist.songs[-1].last_timestamp
            if elapsedTime.total_seconds() < 30:
                log.info("already identified a song less than 30 seconds ago ...")
                await self.send_lastsong_message(ctx, ctx.content) 
                return

        found = False
        self.try_count = 0
        self.is_identifying = True

        while found is False and self.try_count < 5:
            found = await self.try_identify(ctx)
            await asyncio.sleep(5)
            self.try_count += 1
        
        self.is_identifying = False
        if not found:
            log.info('exceeded number of retrys ...')


    async def try_identify(self, ctx = None):

        try:
            if not self.twitch_recorder.is_user_online():
                log.warning(f"can not record because {self.config['channel']} is not online")
                return False

            self.is_identifying = True


            if ctx is None:
                ctx = await self.get_context(Message(channel=self.get_channel(self.config['channel']), content="", author=self.config['botUsername'], raw_data="", tags={}))

            record_length = self.config.get('recordLength', 15)
            file_path = await self.twitch_recorder.record(record_length)
            if self.twitch_recorder.is_blocked:
                log.warning("recording blocked and could not download ...")

            if self.twitch_recorder.is_blocked and self.config['enableVpnRotation'] and self.vpn is not None:
                log.info("switching vpn and trying again ...")
                # connect to a different vpn and try again
                if self.vpn.is_connected: 
                    self.vpn.disconnect()
                    await asyncio.sleep(2) # sleep to let disconnect finish
                
                self.vpn.connect_random()
                await asyncio.sleep(7) # sleep to let init/connect 

                file_path = await self.twitch_recorder.record(record_length)
                if self.twitch_recorder.is_blocked:
                    log.warning("recording blocked again ...")

        except Exception as e:
            log.error(e)
            self.twitch_recorder.is_recording = False
            file_path = None

        if file_path is None or not os.path.exists(file_path):
            await self.send_message(ctx, botreplys.get_trouble_listening_reply(), force_quiet=self.is_silenced)
            self.is_identifying = False
            return False

        try:
            response = self.music_identifier.identify(file_path)
            info = self.music_identifier.get_song_info_from_response(response)
        except Exception as e:
            log.error(e)
            self.music_identifier.is_identifying = False
            info = None

        if info is None:
            msg = botreplys.get_trouble_listening_reply() if self.twitch_recorder.is_blocked else botreplys.get_unknown_song_reply()
            await self.send_message(ctx, msg, force_quiet=self.is_silenced)
            self.is_identifying = False
            return False
            
        song = Song(info)
        was_added = self.playlist.add(song)
        if was_added:
            msg = song.get_current_playing_msg()
            await self.send_message(ctx, msg)
        
        self.is_identifying = False
        self.trigger_count = 0
        return True

    @commands.command(name='majhelp', aliases=['bothelp'])
    async def majhelp(self, ctx):
        await self.send_message(ctx, 'Type "!track" to identify the current song playing. "!last" for last song identified or "!last X" to get last X songs identified.')

    @commands.command(name='add')
    async def add(self, ctx):
        track_info = ctx.content[5:].split(';')

        if len(track_info) < 2:
            await self.send_message(ctx, "command usage: !add song;artist")
            return # ignore bad input

        if track_info[0] in ["song","title", ""] or track_info[1] in ["artist", ""]:
            return # ignore sample input

        if len(self.playlist.songs) > 0:
            elapsedTime = datetime.datetime.now() - self.playlist.songs[-1].last_timestamp
            if elapsedTime.total_seconds() < 15:
                log.info("already added or identified a song less than 15 seconds ago ...")
                await self.send_message(ctx, self.playlist.get_last_song_msg(self.config['identifyCooldown']))
                return

        song = Song({'title': track_info[0].strip(),
                    'artists': [track_info[1].strip()],
                    'added_by': ctx.author.name.lower(),
                    'album': ''})
        self.playlist.add(song)
        
        msg = f'Added: "{song.title}" ║ Artist: {", ".join(song.artists)}'
        await self.send_message(ctx, msg)

    @commands.command(name='remove', aliases=['undo'])
    async def remove(self, ctx):
        if len(self.playlist.songs) == 0:
            return
        
        chat_msgs = ctx.content.split(' ')

        # find last song added by user
        song = None
        idx = len(self.playlist.songs) 
        while idx > 0:
            idx -= 1
            if self.playlist.songs[idx].added_by != "":
                song = self.playlist.songs[idx]
                break

        if song is None:
            return # no song added by user

        # remove song only if added in past 2 minutes or keyword 'force' is used
        elapsedTime = datetime.datetime.now() - song.last_timestamp
        if elapsedTime.total_seconds() < 120 or 'force' in chat_msgs:
            self.playlist.songs.pop(idx)
            msg = f'Removed: "{song.title}" ║ Artist: {", ".join(song.artists)}'
            await self.send_message(ctx, msg)

    @commands.command(name='wrong', aliases=['badbot'])
    async def wrong_song(self, ctx):
        if len(self.playlist.songs) == 0:
            return
        
        chat_msgs = ctx.content.split(' ')

        # find last song added by bot
        song = None
        idx = len(self.playlist.songs) 
        while idx > 0:
            idx -= 1
            if self.playlist.songs[idx].added_by == "":
                song = self.playlist.songs[idx]
                break

        if song is None:
            return # no song added by bot

        # remove song only if added in past 2 minutes or keyword 'force' is used
        elapsedTime = datetime.datetime.now() - song.last_timestamp
        if elapsedTime.total_seconds() < 120 or 'force' in chat_msgs:
            self.playlist.songs.pop(idx)
            msg = f'Removed: "{song.title}" ║ Artist: {", ".join(song.artists)}  ║ Album: {self.album}'
            await self.send_message(ctx, msg)


    @commands.command(name='score')
    async def score(self, ctx):
        if len(self.playlist.songs) == 0:
            return

        if ctx.content == "!score top":
            scores = {}
            for s in self.playlist.songs:
                if s.added_by == "": continue # skip songs added by bot
                scores[s.added_by] = scores.get(s.added_by, 0) + 1

            if len(scores) == 0:
                return # no scores yet
            
            sorted_scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
            first = [i for i in sorted_scores.items()][0]
            msg = f"{first[0]} is in the lead and has ID'ed {first[1]} songs this stream!"

            if len(sorted_scores) > 1:
                second = [i for i in sorted_scores.items()][1]
                msg += f" {second[0]} is right behind with {second[1]} songs ID'ed so far!"

            await self.send_message(ctx, msg)
            return

        
        score = 0
        for s in self.playlist.songs:
            if s.added_by == ctx.author.name.lower():
                score += 1

        if score == 0:
            msg = f"{ctx.author.name}, you have not ID'ed anything yet!"
        elif score == 1:
            msg = f"{ctx.author.name}, you have ID'ed only one song so far this stream!"
        else:
            msg = f"{ctx.author.name}, you have ID'ed {score} songs so far this stream!"
        
        await self.send_message(ctx, msg)

    @commands.command(name="lastsong", aliases=["last"])
    async def lastsong(self,ctx):
        await self.send_lastsong_message(ctx, ctx.content)
        
    async def send_lastsong_message(self, ctx = None, message=""):

        if len(self.playlist.songs) == 0:
            return

        if ctx is None:
            ctx = await self.get_context(Message(channel=self.get_channel(self.config['channel']), content="", author=self.config['botUsername'], raw_data="", tags={}))

        chat_msgs = message.split(' ')
        num_tracks = 1

        if len(chat_msgs) > 1 and chat_msgs[1].isnumeric():
            num_tracks = int(chat_msgs[1])
            if num_tracks < 1 or num_tracks > len(self.playlist.songs):
                num_tracks = 1 # ignore any bad input and default it to last 1 track 


        if num_tracks == 1:
            await self.send_message(ctx, self.playlist.get_last_song_msg(self.config['identifyCooldown']))
        else:
            msg_reply = f"The last {num_tracks} tracks played --> "
            for i in range(1, num_tracks + 1):
                song_info = self.playlist.songs[-i].formatted_str()
                msg_reply += song_info + f' @ {self.playlist.songs[-i].get_last_identified_str()}{SEP_CHAR}'

            await self.send_message(ctx, msg_reply, separator=[SEP_CHAR])

    async def send_currentplaying_message(self, ctx = None, message=""):

        if len(self.playlist.songs) == 0:
            return

        if ctx is None:
            ctx = await self.get_context(Message(channel=self.get_channel(self.config['channel']), content="", author=self.config['botUsername'], raw_data="", tags={}))

        last_song = self.playlist.songs[-1]
        cooldown = self.config.get('identifyCooldown', 30) + 10 # add 10 as padding

        if last_song.get_last_identified_in_seconds() <= cooldown:
            await self.send_message(ctx, last_song.get_current_playing_msg())
            return 

    @commands.command(name='setlist')
    async def setlist(self, ctx):
        msg = "(Title | Artists | Album) --> "
        for song in self.playlist.songs:
            msg += song.formatted_str() + SEP_CHAR

        await self.send_message(ctx, msg, separator=[SEP_CHAR])

    @commands.command(name='quiet')
    async def quiet(self, ctx):
        self.is_silenced = True

        chat_msgs = ctx.content.split(' ')

        if len(chat_msgs) > 1 and chat_msgs[1] == "off":
            self.is_silenced = False

    @commands.command(name='majpoll')
    async def majpoll(self, ctx):
        if ctx.content == "!majpoll end":
            # end poll
            if self.maj_poll is not None and not self.maj_poll.has_ended:
                self.maj_poll.has_ended = True
                self.prev_polls.append(self.maj_poll)
                
                msg = f"The poll has ended: {self.maj_poll.question}? "
                msg += self.maj_poll.get_poll_results()
                await self.send_message(ctx, msg, separator=["-", SEP_CHAR])
            return

        if self.maj_poll is None or self.maj_poll.has_ended:
            # start a new poll
            question = ctx.content[8:].strip()
            self.maj_poll = MajPoll(question)
            await self.send_message(ctx, f"A new poll has started: {question}? Type !vote with your answer")
        elif self.maj_poll is not None:
            # return  question/results of most recent poll  
            msg = f"Current poll: {self.maj_poll.question}? Type !vote with your answer... "
            msg += self.maj_poll.get_poll_results()
            await self.send_message(ctx, msg, separator=["-", SEP_CHAR])

    @commands.command(name='vote')
    async def vote(self, ctx):
        answer = ctx.content[5:].strip()

        if self.maj_poll is not None and len(answer) > 0:
            self.maj_poll.vote(answer, ctx.author.name.lower())

    @commands.command(name='greet')
    async def greet(self, ctx):
        chat_msgs = ctx.content.split(' ')
        greeting = ""
        today = datetime.datetime.today()

        if len(chat_msgs) > 1:
            greeting = botreplys.get_welcome_greeting(ctx.content[6:].strip(), botreplys.get_stream_name_by_day(today.weekday()))
        else:
            greeting = botreplys.get_greeting(today)

        await self.send_message(ctx, greeting)

    async def send_channel_message(self, message, force_quiet=False):
        log.info(message)
        if not force_quiet:
            ws = self._ws
            await ws.send_privmsg(self.config['channel'], message)
    
    async def send_message_batch(self, ctx, messages):
        for m in messages:
            await ctx.send(m)
            await asyncio.sleep(random.uniform(2,3.5))

    async def send_message(self, ctx, message, separator=[" "], force_quiet=False):
        log.info(message)
        if self.config['print_only'] or force_quiet:
            return

        # dont send duplicate message within 3 seconds of sending last message
        elapsed = datetime.datetime.now() - self.last_msg_sent
        if elapsed.total_seconds() <= 3 and message == self.last_msg:
            return

        if len(message) < 500:
            await ctx.send(message)
        else:
            # split message by 500 chunks
            messages = []

            if " " not in separator: separator.append(" ")

            while len(message) > 0:
                message_len = min(498, len(message)) # get next ~500 characters or rest of message
                sub_msg = message[:message_len]
                split_idx = -1
                
                if message_len < 498:
                    messages.append(message)
                    break
                    
                for sep in separator:
                    split_idx = sub_msg[::-1].find(sep) # reverse string and look for separator
                    if split_idx != -1:
                        break
                
                if split_idx not in [-1, 0]:
                    sub_msg = sub_msg[:-split_idx]
                
                messages.append(sub_msg)
                message = message.replace(sub_msg, "")

            await self.send_message_batch(ctx, messages)
        
        self.last_msg = message
        self.last_msg_sent = datetime.datetime.now()

