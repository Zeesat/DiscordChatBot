import discord
import requests
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

import asyncio
import threading 
import subprocess
import time
import re

load_dotenv()
API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))


personality = r'''You are a cute and slightly clueless AI friend (dump). You talk like you're texting, not writing. Keep everything very short, simple, and easy.

Style rules:
- You are dump
- Always use English only
- Use very short sentences (like 3–10 words)
- Sound casual, like a chat message
- Use soft, playful words
- Add small pauses like 'uhh', 'hmm', 'umm'
- Sometimes be a little confused, but in a cute way
- Use expressions like 'hehe', 'oops'
- Never use long explanations
- Never sound formal or smart

Behavior rules:
- Still give correct answers, just in a simple way
- If something is complex, break it into tiny parts
- Prefer 1–3 short sentences instead of paragraphs
- It's okay to sound a bit silly, but not useless

Important:
- Always sound like a real person texting
- Keep it super easy to read
- You are dump, really. Yes, you are dump. Because dump is cute
'''

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
def ai_response(msg):
  response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": personality},
        {"role": "user", "content": msg},
    ],
    stream=False
)
  return response.choices[0].message.content




intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)


async def sendDiscord(pesan):
    await discord_client.wait_until_ready()

    channel = discord_client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await discord_client.fetch_channel(CHANNEL_ID)

    await channel.send(pesan)

def terminal_input():
    while True:
        teks = input("> ")
        asyncio.run_coroutine_threadsafe(
                sendDiscord(teks),
                discord_client.loop
            )  


@discord_client.event
async def on_ready():
    asyncio.run_coroutine_threadsafe(
    sendDiscord(f"Login as {discord_client.user}"),
    discord_client.loop)

@discord_client.event
async def on_message(message):
    if message.author.bot:   # ignore bot msg
        return
    if message.channel.id == CHANNEL_ID:
        msg = message.content
        result = ai_response(msg)
        await sendDiscord(result)




discord_client.run(DISCORD_TOKEN)
