import discord
from discord.ext import commands
import aiohttp
import re
import json
import os
import random
import urllib.parse
import asyncio
from keep_alive import keep_alive

# ========== CONFIGURATION ==========
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
SERVER_IP = os.getenv('SERVER_IP', 'play.zxservers.com')

SERVER_NAME = "ZX Servers"
SERVER_VERSION = "1.12.2"
SERVER_TYPE = "Survival"
OWNER = "Aswanth R"
CREATOR_NAME = "Aswanth R"
BOT_NAME = "ZX AI"
BOT_VERSION = "1.0.0"

MEMORY_FILE = 'zx_memory.json'
# ===================================

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, reconnect=True)

# Memory
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'r') as f:
        memory = json.load(f)
else:
    memory = {}

def save_memory():
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f)
    except:
        pass

def clean_mentions(content, bot_id):
    content = re.sub(f'<@!?{bot_id}>', '', content)
    return content.strip()

# 🎯 BALANCED RESPONSES (Fun but not toxic)
PLAYFUL_ROASTS = [
    "bro 💀",
    "lol",
    "cope",
    "rent free",
    "who asked?",
    "ok buddy",
    "touch grass",
    "skill issue 💀",
    "mad?",
]

MINECRAFT_PLAYFUL = [
    "someone needs diamonds 💎",
    "bro mines with wooden pickaxe",
    "average dirt house enjoyer",
    "got killed by a zombie? 💀",
]

# Friendly responses for when people are actually being mean
FRIENDLY_RESPONSES = [
    "chill bro 😎",
    "no need for that",
    "keep it cool",
    "why so serious?",
]

@bot.event
async def on_ready():
    print(f'✅ {BOT_NAME} online!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        
        if user_id not in memory:
            memory[user_id] = {'context': []}
        
        clean_content = clean_mentions(message.content, bot.user.id)
        
        # Just mention
        if not clean_content:
            await message.channel.send(random.choice([f"yo {message.author.name} 👋", f"sup {message.author.name}"]))
            return
        
        lower_content = clean_content.lower()
        
        # Don't respond to remove/kick/ban requests
        if any(word in lower_content for word in ["remove", "kick", "ban", "delete", "fire"]):
            await message.channel.send(random.choice(["can't do that lol", "not how this works", "nice try", "i'm just a chat bot"]))
            return
        
        # Light roasting only if directly insulted
        direct_insults = ["dumb", "stupid", "idiot", "trash", "suck"]
        if any(insult in lower_content for insult in direct_insults):
            await message.channel.send(random.choice(PLAYFUL_ROASTS))
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            memory[user_id]['context'].append({"role": "assistant", "content": random.choice(PLAYFUL_ROASTS)})
            save_memory()
            return
        
        # Get conversation context
        context = memory[user_id]['context'][-6:]
        context_text = ""
        if context:
            for msg in context[-4:]:
                context_text += f"{'User' if msg['role'] == 'user' else BOT_NAME}: {msg['content']}\n"
        
        memory[user_id]['context'].append({"role": "user", "content": clean_content})
        
        if len(memory[user_id]['context']) > 20:
            memory[user_id]['context'] = memory[user_id]['context'][-20:]
        
        # Prompt for general chat - balanced personality
        prompt = f"""You are {BOT_NAME}, a chill Minecraft bot for {SERVER_NAME}. Creator: {CREATOR_NAME}

{context_text}{message.author.name}: {clean_content}

Personality:
- Answer questions directly (yes/no answers when asked)
- 1-2 sentences max
- Be playful but not mean
- Don't pretend to have moderation powers
- Don't say "I can't help with that"
- Just be a chill bot

Reply:"""
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        reply = await resp.text()
                        reply = reply.strip()
                        
                        # Clean JSON crap
                        if reply.startswith('{'):
                            try:
                                parsed = json.loads(reply)
                                reply = parsed.get('content', parsed.get('response', str(reply)))
                            except:
                                reply = re.sub(r'\{.*?\}', '', reply)
                        
                        reply = reply.replace('\\n', ' ').strip()
                        
                        # Fallback
                        if not reply or len(reply) < 2:
                            reply = random.choice(["lol", "bet", "fr?", "ok"])
                        
                        if len(reply) > 500:
                            reply = reply[:500]
                        
                        # Remove any fake moderation claims
                        if "remove" in reply.lower() or "ban" in reply.lower() or "kick" in reply.lower():
                            reply = random.choice(["lol", "bet", "ok", "fr?"])
                        
                        await message.channel.send(reply)
                        memory[user_id]['context'].append({"role": "assistant", "content": reply})
                        save_memory()
                    else:
                        await message.channel.send(random.choice(["lol", "bet", "fr?"]))
                            
        except:
            await message.channel.send(random.choice(["bruh", "lol", "fr?"]))
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def ip(ctx):
    await ctx.send(f"🎮 `{SERVER_IP}` | {SERVER_VERSION} {SERVER_TYPE}")

@bot.command()
async def rules(ctx):
    await ctx.send(f"**Rules:**\n1. Be cool\n2. No griefing\n3. No hacking\n4. Have fun!")

@bot.command()
async def owner(ctx):
    await ctx.send(f"👑 {OWNER}")

@bot.command()
async def creator(ctx):
    await ctx.send(f"🤖 {CREATOR_NAME} made me")

@bot.command()
async def version(ctx):
    await ctx.send(f"📦 {SERVER_VERSION} Survival | {BOT_NAME} v{BOT_VERSION}")

@bot.command()
async def tips(ctx):
    tips = ["💎 Diamonds at Y=11-12", "🏠 Stairs + slabs = better builds", "🌾 Water = 4 block radius", "⚔️ Crit = jump + hit", "📚 15 bookshelves = lvl 30"]
    await ctx.send(random.choice(tips))

@bot.command()
async def about(ctx):
    await ctx.send(f"🤖 {BOT_NAME} - Minecraft bot for {SERVER_NAME} | Made by {CREATOR_NAME}")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send(f"✅ Cleared")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        count = len(memory[user_id]['context'])
        await ctx.send(f"📊 {count} messages")
    else:
        await ctx.send("📊 No history")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

@bot.command()
async def bothelp(ctx):
    await ctx.send(f"**Commands:** `!ip` `!rules` `!owner` `!creator` `!version` `!tips` `!about` `!stats` `!clear` `!ping` `!bothelp`\n💬 @ mention me to chat!")

keep_alive()
bot.run(DISCORD_TOKEN)
