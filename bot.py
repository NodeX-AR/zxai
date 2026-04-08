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

# ========== CONFIGURATION from Environment Variables ==========
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
SERVER_IP = os.getenv('SERVER_IP', 'play.zxservers.com')

# Server Information
SERVER_NAME = "ZX Servers"
SERVER_VERSION = "1.12.2"
SERVER_TYPE = "Survival"
OWNER = "Aswanth R"

# Creator/Bot Information
CREATOR_NAME = "Aswanth R"
BOT_NAME = "ZX Bot"
BOT_VERSION = "1.0.0"
CREATED_DATE = "2026"
BOT_PERSONALITY = "friendly, helpful, and knowledgeable about everything"

# Use persistent storage for memory
MEMORY_FILE = 'zx_memory.json'

# ===================================

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable not set!")
    exit(1)

# Configure intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot
bot = commands.Bot(
    command_prefix='!', 
    intents=intents, 
    help_command=None,
    reconnect=True
)

# Memory for conversations
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'r') as f:
        memory = json.load(f)
else:
    memory = {}

# Server knowledge base
server_info = f"""
You are {BOT_NAME}, the official bot for {SERVER_NAME} Minecraft server.

🤖 ABOUT YOURSELF:
- Your Name: {BOT_NAME}
- Your Creator: {CREATOR_NAME}
- Created Date: {CREATED_DATE}
- Version: {BOT_VERSION}

Server Details:
- Server Name: {SERVER_NAME}
- Minecraft Version: {SERVER_VERSION}
- Game Mode: {SERVER_TYPE}
- Owner: {OWNER}
- Server IP: {SERVER_IP}

Your Role:
- {BOT_PERSONALITY}
- You can answer ANY question - Minecraft related OR general knowledge
- Keep responses friendly and conversational
- You ONLY respond when mentioned with @{BOT_NAME}
"""

def save_memory():
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f)
    except Exception as e:
        print(f"Error saving memory: {e}")

def clean_mentions(content, bot_id):
    content = re.sub(f'<@!?{bot_id}>', '', content)
    content = re.sub(r'\s+', ' ', content).strip()
    return content

@bot.event
async def on_ready():
    print(f'✅ {BOT_NAME} is online!')
    print(f'👨‍💻 Created by: {CREATOR_NAME}')
    print(f'🎮 Serving {SERVER_NAME} - {SERVER_VERSION} {SERVER_TYPE}')
    print(f'💬 Bot is ready!')

@bot.event
async def on_connect():
    print("🔌 Connected to Discord!")

@bot.event
async def on_disconnect():
    print("⚠️ Disconnected! Reconnecting...")

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
                f"Hey {message.author.name}! 👋 I'm {BOT_NAME}, created by {CREATOR_NAME}. What's up?",
                f"Yo {message.author.name}! 🎮 Need help? Ask me anything!",
                f"Hello {message.author.name}! 💬 How can I help you today?"
            ]
            await message.channel.send(random.choice(responses))
            return
        
        full_prompt = f"""{server_info}

Question from {message.author.name}: {clean_content}

Answer helpfully and concisely."""
        
        memory[user_id]['context'].append({"role": "user", "content": clean_content})
        
        if len(memory[user_id]['context']) > 10:
            memory[user_id]['context'] = memory[user_id]['context'][-10:]
        
        try:
            async with message.channel.typing():
                async with aiohttp.ClientSession() as session:
                    encoded_msg = urllib.parse.quote(full_prompt)
                    url = f"https://text.pollinations.ai/{encoded_msg}"
                    
                    async with session.get(url, timeout=60) as resp:
                        if resp.status == 200:
                            reply = await resp.text()
                            reply = reply.strip()
                            
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            
                            memory[user_id]['context'].append({"role": "assistant", "content": reply})
                            save_memory()
                        else:
                            await message.channel.send("🎮 Having a moment! Try again in a sec.")
                            
        except asyncio.TimeoutError:
            await message.channel.send("⏰ Request timed out! Try again.")
        except aiohttp.ClientError as e:
            print(f"Connection error: {e}")
            await message.channel.send("🌐 Connection issue! Try again.")
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("⚡ Something went wrong! Try again.")
    
    await bot.process_commands(message)

# Commands
@bot.command()
async def ip(ctx):
    await ctx.send(f"🎮 **{SERVER_NAME} IP:** `{SERVER_IP}`\nVersion: {SERVER_VERSION} {SERVER_TYPE}")

@bot.command()
async def rules(ctx):
    await ctx.send(f"**📜 {SERVER_NAME} Rules:**\n1. Be respectful\n2. No griefing\n3. No hacking\n4. Have fun!")

@bot.command()
async def owner(ctx):
    await ctx.send(f"👑 **Server Owner:** {OWNER}")

@bot.command()
async def creator(ctx):
    await ctx.send(f"🤖 I was created by **{CREATOR_NAME}**! 🎮")

@bot.command()
async def version(ctx):
    await ctx.send(f"📦 **{SERVER_NAME}** - {SERVER_VERSION} {SERVER_TYPE}\n🤖 Bot version: {BOT_VERSION}")

@bot.command()
async def tips(ctx):
    tips_list = [
        "💎 Diamonds at Y=11-12!",
        "🏠 Use varied blocks for better builds!",
        "🌾 Water within 4 blocks of crops!",
        "⚔️ Critical hits when falling!",
        "📚 15 bookshelves = level 30 enchantments!"
    ]
    await ctx.send(random.choice(tips_list))

@bot.command()
async def about(ctx):
    await ctx.send(f"**🤖 About {BOT_NAME}:**\n• Creator: {CREATOR_NAME}\n• Version: {BOT_VERSION}\n• Purpose: Helping {SERVER_NAME} community")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send(f"✅ Cleared history, {ctx.author.name}!")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory and 'context' in memory[user_id]:
        msg_count = len(memory[user_id]['context']) // 2
        await ctx.send(f"📊 {ctx.author.name}, we've had {msg_count} conversations!")

@bot.command()
async def bothelp(ctx):
    help_text = f"""**🎮 {BOT_NAME} Commands:**
`!ip` - Server IP
`!rules` - Server rules
`!owner` - Server owner
`!creator` - Who created me
`!about` - About this bot
`!version` - Version info
`!tips` - Minecraft tips
`!stats` - Your stats
`!clear` - Clear history
`!bothelp` - This message

**Chat:** @{BOT_NAME} your question here"""
    await ctx.send(help_text)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓")

# Start the keep-alive server and run the bot
keep_alive()
bot.run(DISCORD_TOKEN)
