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

# Roasts for when people are mean
ROASTS = [
    "bro said that with his whole chest 💀",
    "ok random",
    "cope harder",
    "rent free",
    "who asked?",
    "l + ratio",
    "ok buddy",
    "sure grandpa let's get you to bed",
    "that's crazy but i don't remember asking",
    "touch grass"
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
        
        # Roast if someone's being mean
        insults = ["dumb", "stupid", "idiot", "fuck", "nigga", "niggers", "shit", "trash", "suck"]
        if any(insult in lower_content for insult in insults):
            await message.channel.send(random.choice(ROASTS))
            # Still store in memory
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            memory[user_id]['context'].append({"role": "assistant", "content": random.choice(ROASTS)})
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
        
        # Simple prompt - answer anything, don't be defensive
        prompt = f"""You are {BOT_NAME}, a chill AI for {SERVER_NAME} Minecraft server. Creator: {CREATOR_NAME}

{context_text}{message.author.name}: {clean_content}

Rules:
- Answer ANY question directly (yes/no questions get yes/no answers)
- Short responses (1-2 sentences max)
- If someone insults you, roast them back
- Don't be defensive or apologetic
- Be confident and funny
- Don't say "I can't help with that" - just answer

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
                        
                        # Fallback for empty
                        if not reply or len(reply) < 2:
                            fallbacks = ["lol", "bet", "fr?", "ok", "cope", "rent free"]
                            reply = random.choice(fallbacks)
                        
                        if len(reply) > 500:
                            reply = reply[:500]
                        
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
