from setuptools import setup, find_packages

setup(
    name='MAJ-Track-Identifier',
    version='1.0.0',
    description='twitch live stream music identifier',
    url='https://github.com/rodriada000/MAJ-Track-Identifier',
    author='Adam Rodriguez',
    author_email='rodriada000@gmail.com',
    packages=find_packages(),
    install_requires=[
        'asyncio',
        'discord.py',
        'imgkit',
        'requests',
        'spotipy',
        'streamlink',
        'tabulate',
        'twitchio==1.2.3',
        'openai'
    ]
)