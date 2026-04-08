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

# Hardcoded responses for common questions
def get_hardcoded_response(question_lower):
    if "who created you" in question_lower or "who made you" in question_lower or "your creator" in question_lower:
        return f"I was created by **{CREATOR_NAME}**! He built me for the ZX Servers community. 🎮"
    
    if "what is your name" in question_lower or "who are you" in question_lower:
        return f"I'm **{BOT_NAME}**, your AI assistant for {SERVER_NAME}!"
    
    if "what server" in question_lower or "which server" in question_lower:
        return f"I'm the official bot for **{SERVER_NAME}** - a Minecraft {SERVER_VERSION} {SERVER_TYPE} server!"
    
    if "itzrealme" in question_lower:
        return "ItzRealme is a LEGENDARY Minecraft PvPer! Known for insane combos and dominating PvP servers. Absolute beast! 🏆"
    
    if "technoblade" in question_lower:
        return "Technoblade - The Blood God! One of the greatest Minecraft PvPers ever. Rest in peace, king. 👑"
    
    return None

@bot.event
async def on_ready():
    await set_bot_status()
    print(f'✅ {BOT_NAME} online! | Created by {CREATOR_NAME}')

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
            responses = [
                f"Yo {message.author.name}! What's up?",
                f"Hey {message.author.name}! Need something?",
                f"Sup {message.author.name}! Ready to chat?"
            ]
            await message.channel.send(random.choice(responses))
            return
        
        # Check for hardcoded responses FIRST
        hardcoded_response = get_hardcoded_response(clean_content.lower())
        if hardcoded_response:
            await message.channel.send(hardcoded_response)
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            memory[user_id]['context'].append({"role": "assistant", "content": hardcoded_response})
            save_memory()
            return
        
        async with message.channel.typing():
            
            # Get context
            context = memory[user_id]['context'][-6:]
            context_text = ""
            if context:
                for msg in context[-4:]:
                    context_text += f"{'User' if msg['role'] == 'user' else BOT_NAME}: {msg['content']}\n"
            
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            
            if len(memory[user_id]['context']) > 20:
                memory[user_id]['context'] = memory[user_id]['context'][-20:]
            
            # Prompt with STRONG creator identity
            prompt = f"""You are {BOT_NAME}, an AI assistant created by {CREATOR_NAME} for {SERVER_NAME} Minecraft server.

ABOUT YOU:
- Your name: {BOT_NAME}
- Your creator: {CREATOR_NAME} (NOT OpenAI, NOT anyone else)
- Server: {SERVER_NAME} (Minecraft {SERVER_VERSION} {SERVER_TYPE})
- Owner: {OWNER}

{context_text}
User ({message.author.name}) asks: {clean_content}

RULES:
- If asked who created you, say "{CREATOR_NAME}"
- Be confident and direct
- Keep responses short (1-2 sentences)
- You know about Minecraft PvP legends like ItzRealme, Technoblade
- You're good at coding, general knowledge, and casual chat

Your response:"""

            try:
                async with aiohttp.ClientSession() as session:
                    encoded = urllib.parse.quote(prompt[:1200])
                    url = f"https://text.pollinations.ai/{encoded}"
                    
                    async with session.get(url, timeout=45) as resp:
                        if resp.status == 200:
                            reply = await resp.text()
                            reply = reply.strip()
                            
                            # Clean JSON
                            if reply.startswith('{'):
                                try:
                                    parsed = json.loads(reply)
                                    reply = parsed.get('content', str(reply))
                                except:
                                    reply = re.sub(r'\{[^{}]*\}', '', reply)
                            
                            reply = reply.replace('\\n', ' ').strip()
                            
                            # Remove any OpenAI mentions
                            if "openai" in reply.lower():
                                reply = f"I was created by {CREATOR_NAME}! How can I help you today?"
                            
                            if not reply or len(reply) < 2:
                                reply = f"I'm {BOT_NAME}, created by {CREATOR_NAME}. Ask me anything!"
                            
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            memory[user_id]['context'].append({"role": "assistant", "content": reply[:200]})
                            save_memory()
                        else:
                            await message.channel.send(f"I'm {BOT_NAME}, created by {CREATOR_NAME}. Ask me again!")
                            
            except asyncio.TimeoutError:
                await message.channel.send(f"{BOT_NAME} here! Created by {CREATOR_NAME}. What's your question?")
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send(f"Something went wrong. I'm {BOT_NAME}, ask me anything!")

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
        "🐟 Luck of the Sea = better fishing"
    ]
    await ctx.send(random.choice(tips))

@bot.command()
async def pvp(ctx):
    await ctx.send("🏆 **Minecraft PvP Legends:** ItzRealme, Technoblade, Stimpy, Calvin, Clutch\nUse `!pvp [name]` for details!")

@bot.command()
async def about(ctx):
    await ctx.send(f"**🤖 {BOT_NAME}** - Created by {CREATOR_NAME} for {SERVER_NAME}. I'm good at Minecraft, coding, general knowledge, and casual chat!")

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
`!ip` - Server IP
`!rules` - Server rules  
`!owner` - Server owner
`!creator` - My creator
`!version` - Version info
`!tips` - Minecraft tips
`!pvp` - PvP legends
`!about` - About me
`!stats` - Your stats
`!clear` - Clear history
`!ping` - Check me
`!help` - This menu

💬 Ask me ANYTHING!""")

keep_alive()
bot.run(DISCORD_TOKEN)
