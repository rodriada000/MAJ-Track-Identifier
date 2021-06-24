import json
import discord
import asyncio

class MajBotClient(discord.Client):
    def __init__(self, token, guildName, channelName):
        super().__init__()
        self.token = token
        self.guildName = guildName
        self.channelName = channelName
        self.guild = None
        self.channel = None
        self.is_logged_in = False

    async def init_login(self):
        if not self.is_logged_in:
            await self.login(self.token)
            self.is_logged_in = True
            print("connected ...")

    async def init_channel(self):
        guilds = await self.fetch_guilds(limit=150).flatten()
        for g in guilds:
            if g.name == self.guildName:
                self.guild = g
                break

        if self.guild is not None:
            channels = await self.guild.fetch_channels()
            for c in channels:
                if c.name == self.channelName:
                    self.channel = c
                    break

        return self.channel is not None

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def close_client(self):
        try:
            self.is_logged_in = False
            await self.close()
        except Exception as e:
            pass 

    async def send_message(self, message, filename=None):

        await self.init_login()
        is_ready = await self.init_channel()
        
        if not is_ready:
            print("could not get channel.")
            return

        if filename is None:
            await self.channel.send(message)
        else:
            with open(filename, 'rb') as fp:
                await self.channel.send(content=message, file=discord.File(fp, 'setlist.png'))

        self.close_client()

        


async def sample_connect():
    config = {}

    with open('.\\config.json') as f:
        config = json.load(f)

    client = MajBotClient(token=config['discord']['botToken'], guildName=config['discord']['guildName'], channelName=config['discord']['channelName'])
    await client.init_login()
    is_ready = await client.init_channel()
    print(is_ready)

    await client.close_client()
    # await client.send_message("This is a test. hello everyone", filename="pyplot-table-demo.png")



# if __name__ == "__main__":
    # asyncio.run(sample_connect())