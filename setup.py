from setuptools import setup, find_packages

setup(
    name='MAJ-Track-Identifier',
    version='0.0.1',
    description='twitch live stream music identifier',
    url='https://github.com/rodriada000/MAJ-Track-Identifier',
    author='Adam Rodriguez',
    author_email='rodriada000@gmail.com',
    packages=find_packages(),
    install_requires=[
        'asyncio',
        'requests',
        'spotipy'
        'streamlink',
        'tabulate',
        'twitchio'
    ]
)