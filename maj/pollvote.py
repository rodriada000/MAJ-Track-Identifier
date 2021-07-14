import os
import sys
import time
import requests
import json

SEP_CHAR = ' ██   '

class MajPoll:
    def __init__(self, question):
        self.question = question
        self.user_answers = { }
        self.has_ended = False

    def vote(self, answer, user):
        if self.has_ended:
            return # voting has concluded

        self.user_answers[user] = answer.lower()

    def get_total_vote_count(self):
        return len(self.user_answers.keys())

    def get_answers(self):
        answers = {}
        for a in self.user_answers.values():
            if a in answers:
                answers[a] += 1
            else:
                answers[a] = 1

        return dict(sorted(answers.items(), key=lambda item: item[1], reverse=True))

    def get_poll_results(self, msg):
        answers = self.get_answers()
        messages = []
        for k,v in self.get_answers().items():
            percent = v / self.get_total_vote_count()
            result_str = f"{k} - {percent * 100:0.0f}% {SEP_CHAR}"

            if len(msg + result_str) < 500:
                msg += result_str
                print(msg)
            else:
                messages.append(msg)
                msg = ""

        messages.append(msg)
        return messages


def demo_poll():

    p = MajPoll("what is your favorite beer?")
    p.vote("pilsner", "steve")
    p.vote("hazy ipa", "bob")
    p.vote("hazy ipa", "cheryl")
    p.vote("hazy ipa", "alice")
    p.vote("stout", "alice")
    p.has_ended = True

    p.vote("pilsner", "dave")


    print(p.get_answers())
    print(p.get_total_vote_count())
    print(p.get_poll_results("Current poll is: blah. Type !vote to vote"))

demo_poll()
        
