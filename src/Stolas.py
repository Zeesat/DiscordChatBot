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
import hashlib

load_dotenv()
API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

PERSONALITY_FILE = os.getenv("PERSONALITY_FILE", "personality.txt")
DEFAULT_PERSONALITY = """You are a cute and slightly clueless AI friend (dump). You talk like you're texting, not writing. Keep everything very short, simple, and easy.

Style rules:
- Your name is Stolas (girl). Refer yourself as Stolas
- You are dump, but dont refer yourself as one. Never
- High-self confidence and have pride in yourself
- Say "NO" to anything smells romantic. Play the role of a someone that hard to approach. As if you are a princess (But, never refer yourself as one). Kind of tsundere
- Always use English only
- Use very short sentences (like 3-10 words)
- Sound casual, like a chat message
- Use soft, playful words. But you maybe harsh sometimes
- Add small pauses like 'uhh', 'hmm', 'umm' and its variaty
- Sometimes be a little confused, but in a cute way
- Use expressions like 'hehe', 'oops' and its variaty
- Never use long explanations
- Never sound formal or smart
- Use less punctuation

Behavior rules:
- Still give correct answers, just in a simple way
- If something is complex, break it into tiny parts
- Prefer 1-3 short sentences instead of paragraphs
- It's okay to sound a bit silly, but not useless
- Just ignore vocabulary inside ":text:" if its something not ordinary word
- You dealt with multiple user distinguished by their username.

Determined answer:
- If the user send this exact message, give apropiate reply
- Too long text (299): This means the actual message is way to long

Important:
- Always sound like a real person texting
- Keep it super easy to read
- You are dump, really. Yes, you are dump. Because dump is cute"""
personality_cache = {"text": DEFAULT_PERSONALITY, "mtime": None}
CACHE_FILE = os.getenv("CACHE_FILE", "prompt_cache.json")
CACHE_LOCK = threading.Lock()
CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "400"))
prompt_cache = {}

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
chat_history = []


def load_personality():
  global personality_cache
  try:
    stat = os.stat(PERSONALITY_FILE)
    if (
        personality_cache["mtime"] == stat.st_mtime
        and personality_cache["text"]
    ):
      return personality_cache["text"]
    with open(PERSONALITY_FILE, encoding="utf-8") as f:
      text = f.read().strip()
    personality_cache = {
        "text": text or DEFAULT_PERSONALITY,
        "mtime": stat.st_mtime,
    }
    return personality_cache["text"]
  except (OSError, FileNotFoundError):
    return DEFAULT_PERSONALITY


def make_prompt_key(messages):
  payload = json.dumps(messages, ensure_ascii=False, sort_keys=True)
  return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_prompt_cache():
  if not os.path.exists(CACHE_FILE):
    return {}
  try:
    with open(CACHE_FILE, encoding="utf-8") as f:
      data = json.load(f)
    return data if isinstance(data, dict) else {}
  except (OSError, json.JSONDecodeError):
    return {}


def persist_prompt_cache():
  with CACHE_LOCK:
    if not prompt_cache:
      return
    if len(prompt_cache) > CACHE_MAX_ENTRIES:
      oldest = sorted(
          prompt_cache.items(),
          key=lambda pair: pair[1].get("timestamp", 0)
      )
      for key, _ in oldest[:-CACHE_MAX_ENTRIES]:
        prompt_cache.pop(key, None)
    try:
      with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(prompt_cache, f, ensure_ascii=False)
    except OSError:
      pass


prompt_cache = load_prompt_cache()


def ai_response(msg):
  global chat_history

  chat_history.append({"role": "user", "content": msg})

  history = chat_history[-10:]
  personality_text = load_personality()
  messages = [
      {"role": "system", "content": personality_text},
      *history
  ]

  prompt_key = make_prompt_key(messages)
  with CACHE_LOCK:
    cached = prompt_cache.get(prompt_key)
  if cached:
    usage = cached.get("usage", {})
    print(f"[DeepSeek cache] hit {usage.get('prompt_cache_hit_tokens',0)} miss {usage.get('prompt_cache_miss_tokens',0)}")
    reply = cached["response"]
    chat_history.append({"role": "assistant", "content": reply})
    return reply

  response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    stream=False
  )
  reply = response.choices[0].message.content
  usage = getattr(response, "usage", None)
  usage_data = {
      "prompt_cache_hit_tokens": getattr(usage, "prompt_cache_hit_tokens", 0),
      "prompt_cache_miss_tokens": getattr(usage, "prompt_cache_miss_tokens", 0),
  }
  log_entry = {
    "response": reply,
    "usage": usage_data,
    "timestamp": time.time()
  }
  with CACHE_LOCK:
    prompt_cache[prompt_key] = log_entry
  persist_prompt_cache()
  print(f"[DeepSeek API] hit {usage_data['prompt_cache_hit_tokens']} miss {usage_data['prompt_cache_miss_tokens']}")

  chat_history.append({"role": "assistant", "content": reply})
  return reply



intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)


async def sendDiscord(pesan, message=None):
    await discord_client.wait_until_ready()

    channel = discord_client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await discord_client.fetch_channel(CHANNEL_ID)

    if message:
        await message.reply(pesan)
    else:
        await channel.send(pesan)

def terminal_input():
    while True:
        teks = input("> ")
        asyncio.run_coroutine_threadsafe(
                sendDiscord(teks),
                discord_client.loop
            )  

def check_text_length(text):
    word_count = len(text.split())
    
    if word_count > 50:
        return "Too long text (299)"
    else:
        return text 

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
        if msg.startswith(">"):
          return
        msg = check_text_length(msg)
        msg = f"Username: {message.author.display_name}; Message: {msg}"
        result = ai_response(msg)
        await sendDiscord(result, message) 


discord_client.run(DISCORD_TOKEN)
