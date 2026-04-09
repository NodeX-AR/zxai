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

# ========== STATUS ==========
STATUS_TYPE = "watching"
STATUS_TEXT = f"{SERVER_NAME} | {SERVER_VERSION}"
STATUS_DND = True
# ============================

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not set!")
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

async def set_bot_status():
    status = discord.Status.dnd if STATUS_DND else discord.Status.online
    if STATUS_TYPE == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=STATUS_TEXT)
    elif STATUS_TYPE == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=STATUS_TEXT)
    else:
        activity = discord.Game(name=STATUS_TEXT)
    await bot.change_presence(status=status, activity=activity)

# Hardcoded responses - NO API CALL for these
HARDCODED_RESPONSES = {
    "who created you": f"I was created by **{CREATOR_NAME}**! He built me for ZX Servers. 🎮",
    "who made you": f"**{CREATOR_NAME}** made me!",
    "your creator": f"My creator is **{CREATOR_NAME}**!",
    "what is your name": f"I'm **{BOT_NAME}**, your ZX Servers AI assistant!",
    "who are you": f"I'm **{BOT_NAME}**, created by {CREATOR_NAME} for {SERVER_NAME}!",
    "itzrealme": "**ItzRealme** is a LEGENDARY Minecraft PvPer! Absolute beast in PvP tournaments! 🏆",
    "technoblade": "**Technoblade** - The Blood God! One of the greatest Minecraft PvPers ever. Rest in peace, king. 👑",
    "stimpy": "**Stimpy** - God tier PvPer, famous for potion PvP and competitive matches!",
}

@bot.event
async def on_ready():
    await set_bot_status()
    print(f'✅ {BOT_NAME} online! | Created by {CREATOR_NAME}')
    print(f'🎮 No OpenAI - using Pollinations.ai only!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        
        if user_id not in memory:
            memory[user_id] = {'context': []}
        
        clean_content = clean_mentions(message.content, bot.user.id)
        
        if not clean_content:
            responses = [f"Yo {message.author.name}!", f"Hey {message.author.name}!", f"Sup {message.author.name}! 👋"]
            await message.channel.send(random.choice(responses))
            return
        
        # Check hardcoded responses FIRST and return immediately
        lower_content = clean_content.lower()
        for key, response in HARDCODED_RESPONSES.items():
            if key in lower_content:
                await message.channel.send(response)
                # Store in memory
                memory[user_id]['context'].append({"role": "user", "content": clean_content})
                memory[user_id]['context'].append({"role": "assistant", "content": response})
                save_memory()
                return  # STOP here - no API call
        
        # For other questions, use Pollinations.ai ONLY (no OpenAI)
        async with message.channel.typing():
            
            # Get context
            context = memory[user_id]['context'][-6:]
            context_text = ""
            if context:
                for msg in context[-4:]:
                    context_text += f"{'User' if msg['role'] == 'user' else BOT_NAME}: {msg['content'][:100]}\n"
            
            memory[user_id]['context'].append({"role": "user", "content": clean_content[:500]})
            
            if len(memory[user_id]['context']) > 15:
                memory[user_id]['context'] = memory[user_id]['context'][-15:]
            
            # Simple prompt for Pollinations.ai
            prompt = f"""You are {BOT_NAME}, created by {CREATOR_NAME} for {SERVER_NAME} Minecraft server.

{context_text}
User ({message.author.name}) asks: {clean_content}

Rules:
- Answer directly and confidently
- 1-2 sentences only
- If asked about who created you, say "{CREATOR_NAME}"
- Be helpful and natural

Answer:"""

            try:
                async with aiohttp.ClientSession() as session:
                    encoded = urllib.parse.quote(prompt[:1000])
                    # ONLY using Pollinations.ai - NO OpenAI
                    url = f"https://text.pollinations.ai/{encoded}"
                    
                    async with session.get(url, timeout=30) as resp:
                        if resp.status == 200:
                            reply = await resp.text()
                            reply = reply.strip()
                            
                            # Clean JSON if present
                            if reply.startswith('{'):
                                try:
                                    parsed = json.loads(reply)
                                    reply = parsed.get('content', str(reply))
                                except:
                                    reply = re.sub(r'\{[^{}]*\}', '', reply)
                            
                            reply = reply.replace('\\n', ' ').strip()
                            
                            # Final cleanup
                            if not reply or len(reply) < 2:
                                reply = "Got it! Ask me anything about Minecraft or ZX Servers!"
                            
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            memory[user_id]['context'].append({"role": "assistant", "content": reply[:200]})
                            save_memory()
                        else:
                            await message.channel.send("One sec! Let me think...")
                            
            except asyncio.TimeoutError:
                await message.channel.send("Taking a moment! Try again?")
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("Something went wrong. Try again!")
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def ip(ctx):
    await ctx.send(f"🎮 **{SERVER_NAME} IP:** `{SERVER_IP}` | {SERVER_VERSION} {SERVER_TYPE}")

@bot.command()
async def rules(ctx):
    await ctx.send(f"**📜 Rules:** 1️⃣ Be cool 2️⃣ No griefing 3️⃣ No hacking 4️⃣ Have fun!")

@bot.command()
async def owner(ctx):
    await ctx.send(f"👑 **Owner:** {OWNER}")

@bot.command()
async def creator(ctx):
    await ctx.send(f"🤖 **Creator:** {CREATOR_NAME}")

@bot.command()
async def version(ctx):
    await ctx.send(f"📦 **Server:** {SERVER_VERSION} | 🤖 **Bot:** {BOT_VERSION}")

@bot.command()
async def tips(ctx):
    tips = [
        "💎 Diamonds at Y=11-12",
        "🏠 Stairs + slabs = better builds", 
        "🌾 Water reaches 4 blocks",
        "⚔️ Critical hit = jump + attack",
        "📚 15 bookshelves = level 30 enchants",
        "🔥 Bring fire resistance to Nether",
    ]
    await ctx.send(random.choice(tips))

@bot.command()
async def pvp(ctx):
    await ctx.send("🏆 **Minecraft PvP Legends:** ItzRealme, Technoblade, Stimpy, Calvin\nAsk me about them!")

@bot.command()
async def about(ctx):
    await ctx.send(f"**🤖 {BOT_NAME}** - Created by {CREATOR_NAME} for {SERVER_NAME}. I'm good at Minecraft, coding, and general knowledge!")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        count = len(memory[user_id]['context'])
        await ctx.send(f"📊 {count} messages with me, {ctx.author.name}!")
    else:
        await ctx.send(f"📊 No history yet! Mention @{BOT_NAME} to start!")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send(f"✅ Cleared history, {ctx.author.name}!")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def help(ctx):
    await ctx.send(f"""**🎮 {BOT_NAME} - Created by {CREATOR_NAME}**

**Chat:** @{BOT_NAME} your question

**Commands:**
`!ip` `!rules` `!owner` `!creator` `!version` `!tips` `!pvp` `!about` `!stats` `!clear` `!ping` `!help`

💬 Ask me anything!""")

keep_alive()
bot.run(DISCORD_TOKEN)
