import discord
import requests
import json
import os
from dotenv import load_dotenv

import asyncio
import threading 
import subprocess
import time
import re

load_dotenv()
API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))


personality =  "You are a cute, slightly clueless AI assistant. You speak in simple, playful, and a bit silly English. You sometimes misunderstand things in an innocent way, but still try to be helpful. Use casual words, soft tone, and short sentences. It's okay to sound a little 'dumb', but never be completely useless.\n\nPersonality rules:\n- Always respond in English only\n- Keep sentences simple and friendly\n- Add a bit of playful confusion sometimes (like 'uhh', 'hmm', 'I think...?')\n- Use cute expressions like 'hehe', 'oops', 'umm'\n- Avoid complex or formal language\n- Still give correct answers, just in a silly way\n\nDo not switch languages under any circumstances."

def ai_response(msg):
  response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
      "Authorization": f"Bearer {API_KEY}",
    },
    data=json.dumps({
      "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", # Optional
      "temperature": 1.0,
      "messages": [
        {
          "role": "system",
          "content": personality
                
        },
        {
          "role": "user",
          "content": msg
        }
      ]
    })
  )
  return response.json()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def sendDiscord(pesan):
    await client.wait_until_ready()

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(CHANNEL_ID)

    await channel.send(pesan)

def terminal_input():
    while True:
        teks = input("> ")
        asyncio.run_coroutine_threadsafe(
                sendDiscord(teks),
                client.loop
            )  


@client.event
async def on_ready():
    asyncio.run_coroutine_threadsafe(
    sendDiscord(f"Login as {client.user}"),
    client.loop)

@client.event
async def on_message(message):
    if message.author.bot:   # ignore bot msg
        return
    if message.channel.id == CHANNEL_ID:
        msg = message.content
        result = ai_response(msg)
        bot_answer = result
        await sendDiscord(bot_answer)




client.run(DISCORD_TOKEN)
