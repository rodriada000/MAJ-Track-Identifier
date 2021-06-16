import random

GREETINGS = ["/me has landed!",
             "/me is in the house!",
             "a wild majmusicbot has appeared.",
             "yo yo yo it's your favorite bot bud !",
             "It's your friendly neighborhood bot bud!"]

DISCO_GREETINGS = ["/me would like to welcome you to Disco Friday!",
                   "Who's ready for Disco Friday?! this bot is ready!",
                   "/me is ready to shake it for Disco Friday!",
                   "/me learned how to spell D-I-S-C-O F-R-I-D-A-Y !"]

JAZZ_GREETINGS = ["/me would like to welcome you to Monday Jazz Club!",
                  "Who's ready for a relaxing Monday Jazz Club? this bot is.",
                  "/me is ready to take it easy for Monday Jazz Club..."]

SOUL_GREETINGS = ["/me would like to welcome you to Soulful Wednesday!",
                  "Who's ready for Soulful Wednesday?! this bot is ready!",
                  "/me is ready to get soulful for Soulful Wednesday!",
                  "choo choo all aboard the soul train for Soulful Wednesday!"]

UNKNOWN_REPLYS = ["I can't tell what's playing...",
                  "I'm not too sure what's playing right now...",
                  "beep boop. I do not know this song...",
                  "I have no idea what song is playing..."]

CANT_RECORD_REPLYS = ["I had trouble listening. Please try again ...",
                      "I didn't get that. Please try again ...",
                      "Could you try again please? I'm not sure I heard that."]

ALREADY_IDENTIFYING_REPLYS = ["Gimme a second, I'm still trying to listen.",
                              "I'm already trying to identify!"]


def get_greeting(date):
    if date.weekday() == 0:
        return JAZZ_GREETINGS[random.randint(0, len(JAZZ_GREETINGS) - 1)]
    elif date.weekday() == 2:
        return SOUL_GREETINGS[random.randint(0, len(SOUL_GREETINGS) - 1)]
    elif date.weekday() == 4:
        return DISCO_GREETINGS[random.randint(0, len(DISCO_GREETINGS) - 1)]
    else:
        return GREETINGS[random.randint(0, len(GREETINGS) - 1)]


def get_unknown_song_reply():
    return UNKNOWN_REPLYS[random.randint(0, len(UNKNOWN_REPLYS) - 1)]


def get_trouble_listening_reply():
    return CANT_RECORD_REPLYS[random.randint(0, len(CANT_RECORD_REPLYS) - 1)]


def get_already_listening_reply():
    return ALREADY_IDENTIFYING_REPLYS[random.randint(0, len(ALREADY_IDENTIFYING_REPLYS) - 1)]
