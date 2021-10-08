import random
import json
import datetime

GREETINGS = ["/me has landed!",
             "/me is in the house!",
             "a wild majmusicbot has appeared.",
             "yo yo yo it's your favorite bot bud !",
             "It's your friendly neighborhood bot bud!"]

DISCO_GREETINGS = ["/me would like to welcome you to Disco Friday!",
                   "Who's ready for Disco Friday?! this bot is ready!",
                   "/me is ready to shake it for Disco Friday!",
                   "/me learned how to spell D-I-S-C-O F-R-I-D-A-Y !",
                   "/me is ready to boogy down for Disco Friday!",
                   "/me wants to party for Disco Friday!"]

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
                  "I have no idea what song is playing...",
                  "Can not identify the current song...",
                  "I don't think I know what song this is. try again?"]

CANT_RECORD_REPLYS = ["I had trouble listening. Please try again ...",
                      "I didn't get that. Please try again ...",
                      "Could you try again please? I'm not sure I heard that.",
                      "Failed to record the stream. Please try again ..."]

ALREADY_IDENTIFYING_REPLYS = ["Gimme a second, I'm still trying to listen.",
                              "I'm always listening, sometimes I just don't know yet!",
                              "I'm trying my best to look up this song...",
                              "I'm trying to figure it out. If you know it then use !add song_title;artist_name",
                              "I'm hearing the song but still trying to identify!",
                              "I'm no Shazam - give me a minute!",
                              "Hold on... I'm trying here!",
                              "Have faith I'm still trying ...",
                              "I'll figure it out one day ..."
                              "I'm already trying to identify!"]

WELCOME_GREETINGS = ["Welcome {0} to {1}!"
                    ,"Hey there {0}! Thanks for joining {1}!"
                    ,"Hey hey hey {0} is in the house! Welcome to {1}!"
                    ,"Looks like {0} just joined us! Everyone make sure to say hi and welcome them to {1}!"
                    ,"Yo yo yo {0}. Thanks for joining {1}!"
                    ,"Hi {0}! Glad you could make it to {1}!"]

chat_intents = {}

def load_chat_intents(path_to_json):
    global chat_intents
    with open(path_to_json, 'r') as f:
        chat_intents = json.load(f)["intents"]
    
    # ensure all patterns are lowercase
    for intent in chat_intents:
        intent["patterns"] = [p.lower() for p in intent["patterns"]]


def get_intent_tag(message):
    if message is None or message == "":
        return None

    words = [m.lower() for m in message.split()]

    for intent in chat_intents:
        for pattern in intent["patterns"]:
            pattern_words = pattern.split()
            if len(pattern_words) > 1 and pattern in message.lower():
                return intent["tag"]
            elif len(pattern_words) == 1 and pattern in words:
                return intent["tag"]
    
    return None

def get_intent_response(tag, username="", day_of_week=""):
    for intent in chat_intents:
        if tag == intent["tag"]:
            resp_str = random.choice(intent["responses"])
            return resp_str.format(username, day_of_week)
    
    return None

def get_greeting(date):
    if date.weekday() == 0:
        return (JAZZ_GREETINGS + GREETINGS)[random.randint(0, len(JAZZ_GREETINGS + GREETINGS) - 1)]
    elif date.weekday() == 2:
        return (SOUL_GREETINGS + GREETINGS)[random.randint(0, len(SOUL_GREETINGS + GREETINGS) - 1)]
    elif date.weekday() == 4:
        return (DISCO_GREETINGS + GREETINGS)[random.randint(0, len(DISCO_GREETINGS + GREETINGS) - 1)]
    else:
        return GREETINGS[random.randint(0, len(GREETINGS) - 1)]


def get_unknown_song_reply():
    return UNKNOWN_REPLYS[random.randint(0, len(UNKNOWN_REPLYS) - 1)]


def get_trouble_listening_reply():
    return CANT_RECORD_REPLYS[random.randint(0, len(CANT_RECORD_REPLYS) - 1)]


def get_already_listening_reply():
    return ALREADY_IDENTIFYING_REPLYS[random.randint(0, len(ALREADY_IDENTIFYING_REPLYS) - 1)]

def get_welcome_greeting(person, day):
    return WELCOME_GREETINGS[random.randint(0, len(WELCOME_GREETINGS) - 1)].format(person, day)


def get_stream_name_by_day(weekday, default="My Analog Journal Stream"):
    names = ["Jazz Club Monday", default, "Soulful Wednesday", default, "Disco Friday", "Out of the Ordinary Saturday", default]
    if weekday < 0 or weekday >= len(names):
        return default
    return names[weekday]

def get_reply_based_on_message(message, author_name="", date_time=None):
    # look for keywords that can be replied to
    words = message.split()
    stream_day = get_stream_name_by_day(date_time.weekday())

    tag = get_intent_tag(message)
    if tag is not None:
        return get_intent_response(tag, author_name, stream_day)
    
    return ""

if __name__ == "__main__":
    # example of replys
    load_chat_intents('intents.json')
    print(get_reply_based_on_message("good bot", "bob", datetime.datetime.today()))
    print(get_reply_based_on_message("bad bot", "bob", datetime.datetime.today()))
    print(get_reply_based_on_message("hi", "bob", datetime.datetime.today()))

