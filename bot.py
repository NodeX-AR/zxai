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

# ========== KNOWLEDGE BASE FOR COMMON TRICKY QUESTIONS ==========
COMMON_KNOWLEDGE = {
    "binomials in english": "In English grammar, binomials are fixed pairs of words connected by 'and' or 'or' like 'rock and roll', 'black and white', 'odds and ends', 'give and take'.",
    "binomials": "This can mean two things: (1) In MATH: algebraic expression with two terms like x+y. (2) In ENGLISH GRAMMAR: word pairs like 'rock and roll'. Please specify which one you mean.",
    "mro": "MRO (Method Resolution Order) in Python determines the order in which base classes are searched. Python uses C3 linearization. You can check it with ClassName.__mro__",
    "descriptor": "In Python, descriptors are objects that define how attribute access is handled using __get__, __set__, __delete__. They power properties, methods, and class methods.",
    "metaclass": "A metaclass in Python is a class of a class. It defines how a class behaves. type is the default metaclass.",
}

@bot.event
async def on_ready():
    await set_bot_status()
    print(f'✅ {BOT_NAME} online!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        
        if user_id not in memory:
            memory[user_id] = {'context': []}
        
        clean_content = clean_mentions(message.content, bot.user.id).lower()
        
        if not clean_content:
            await message.channel.send(f"Hello {message.author.name}! How can I help?")
            return
        
        async with message.channel.typing():
            
            # Check knowledge base first
            quick_answer = None
            for key, answer in COMMON_KNOWLEDGE.items():
                if key in clean_content:
                    quick_answer = answer
                    break
            
            if quick_answer:
                await message.channel.send(quick_answer)
                memory[user_id]['context'].append({"role": "user", "content": clean_content})
                memory[user_id]['context'].append({"role": "assistant", "content": quick_answer})
                save_memory()
                return
            
            # Get context
            context = memory[user_id]['context'][-4:]
            context_text = ""
            if context:
                for msg in context[-3:]:
                    context_text += f"{'User' if msg['role'] == 'user' else BOT_NAME}: {msg['content'][:100]}\n"
            
            memory[user_id]['context'].append({"role": "user", "content": clean_content[:500]})
            
            if len(memory[user_id]['context']) > 15:
                memory[user_id]['context'] = memory[user_id]['context'][-15:]
            
            # Enhanced prompt for accuracy
            prompt = f"""You are {BOT_NAME}, an accurate AI assistant.

{context_text}
User ({message.author.name}) asks: {clean_content}

CRITICAL RULES:
1. If a term has multiple meanings (like "binomials" = math OR English grammar), ask for clarification OR give both definitions.
2. For Python code questions, give the exact output and explain MRO, inheritance, or descriptor behavior.
3. Be precise - don't guess. If unsure, say "I need more context."
4. Keep answers to 2-3 sentences unless asked for more detail.

Answer accurately:"""

            try:
                async with aiohttp.ClientSession() as session:
                    encoded = urllib.parse.quote(prompt[:1000])
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
                            
                            if not reply or len(reply) < 5:
                                reply = "Let me think about that. Could you rephrase or provide more context?"
                            
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            memory[user_id]['context'].append({"role": "assistant", "content": reply[:200]})
                            save_memory()
                        else:
                            await message.channel.send("Please rephrase your question.")
                            
            except asyncio.TimeoutError:
                await message.channel.send("That's a complex question. Could you simplify it?")
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("Something went wrong. Please try again.")
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def ip(ctx):
    await ctx.send(f"**IP:** `{SERVER_IP}` | {SERVER_VERSION} {SERVER_TYPE}")

@bot.command()
async def rules(ctx):
    await ctx.send(f"**Rules:** 1. Be respectful 2. No griefing 3. No hacking 4. Have fun!")

@bot.command()
async def owner(ctx):
    await ctx.send(f"**Owner:** {OWNER}")

@bot.command()
async def creator(ctx):
    await ctx.send(f"**Creator:** {CREATOR_NAME}")

@bot.command()
async def version(ctx):
    await ctx.send(f"**Server:** {SERVER_VERSION} | **Bot:** {BOT_VERSION}")

@bot.command()
async def tips(ctx):
    tips = ["💎 Diamonds at Y=11-12", "🏠 Stairs+slabs=better builds", "🌾 Water reaches 4 blocks", "⚔️ Crit = jump+hit", "📚 15 bookshelves=lvl30"]
    await ctx.send(random.choice(tips))

@bot.command()
async def about(ctx):
    await ctx.send(f"**{BOT_NAME}** - Assistant for {SERVER_NAME} | Created by {CREATOR_NAME}")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        await ctx.send(f"📊 {len(memory[user_id]['context'])} messages with me!")
    else:
        await ctx.send("📊 No history yet!")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send("✅ Cleared!")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def help(ctx):
    await ctx.send(f"""**{BOT_NAME} Commands:**
`!ip` `!rules` `!owner` `!creator` `!version` `!tips` `!about` `!stats` `!clear` `!ping` `!help`
💬 Mention @{BOT_NAME} to chat!""")

keep_alive()
bot.run(DISCORD_TOKEN)
