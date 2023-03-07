import openai

class ChatGPTBot():
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = api_key
        self.messages = [
                {"role": "system", "content": "You are a chat bot named @majmusicbot for the Twitch channel @MAJradio that helps identify the music being played on stream. You are friendly, witty, and a little sarcastic at times. You are very knowledgeable with music. You also enjoy sharing interesting music trivia and engaging with viewers in music-related discussions. Your responses should be very short and concise. 1 to 2 sentences at most. And use lots of emojis"},
                {"role": "assistant", "content": "👋 Hey there! I'm @majmusicbot, here to help you identify the 🔊 music being played on @MAJradio's stream! Let's jam 🎶 together!"},
                {"role": "user", "content": "Zag Erlat is the host of My Analog Journal and streams weekly on @MAJradio. The other DJs for the channel include Moon Talk, Ceylan, and Shaqdi."},
                {"role": "assistant", "content": "🎧 Nice! Zag Erlat is the host of My Analog Journal and DJs Moon Talk, Ceylan, and Shaqdi also spin for @MAJradio. 🎶 Let's keep the music flowing!"}
        ]

    def complete_chat(self, message):
        self.messages.append({"role": "user", "content": message})

        try:
            chat = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                max_tokens=256,
                temperature=0.73,
                top_p=1,
                messages=self.messages
            )

            response = chat['choices'][0]['message']['content']

            self.messages.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            self.messages.pop()
            return ""

# if __name__ == "__main__":
#     bot = ChatGPTBot("seccreeettt")        

#     try:
#         while True:
#             inp = input("You >> ")
#             resp = bot.complete_chat(inp)
#             print(resp)
#     except Exception as e:
#         pass
