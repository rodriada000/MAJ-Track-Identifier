# MAJ-Track-Identifier
Attempts to identify the song currently playing from a twitch live stream. Originally made to support the channel [My Analog Journal](https://www.youtube.com/channel/UC8TZwtZ17WKFJSmwTZQpBTA).


### How it Works
- The bot will start recording once it receives the command in chat "!track" (or "!tune", "!playing"). If it is already identifying at the moment then it will ignore the command.
- The bot records around 15 seconds of the Twitch live stream using [streamlink](https://github.com/streamlink/streamlink)
- When the recording is blocked by twitch (due to rate limiting on their own API) the bot will switch vpn connections and try again
- The recording is sent to [ACR Cloud](https://www.acrcloud.com/music-recognition/) to identify the song
- The bot reads the ACR Cloud response  and sends a message back to Twitch chat with the song info
- The identified songs are saved to a setlist .json file

### Setup
* Install requirements from `setup.py`
* Create a `config.json` file in the same directory as `bot.py` and fill out the required config info. See `config.example.json` for a template of what needs to be in the config.
* Run `python .\bot.py`

### Project Breakdown
There are four main components to this project:
* `twitchrecorder.py` - handles recording of the live stream
* `identifier.py` - handles sending request to ACR and identifying song
* `vpnrotator.py` - handles connecting and disconnecting to various vpn connections you have configured with [Open VPN](https://openvpn.net/vpn-client/)
* `bot.py` - all the bot setup and command handling
