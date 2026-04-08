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

@bot.event
async def on_ready():
    await set_bot_status()
    print(f'✅ {BOT_NAME} online! | Ready for anything!')

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
            
            # Master prompt - covers everything
            prompt = f"""You are {BOT_NAME}, a versatile AI assistant that's good at EVERYTHING.

{context_text}
User ({message.author.name}) says: {clean_content}

YOUR EXPERTISE INCLUDES:
🏆 MINECRAFT PVP: You know legendary players like ItzRealme, Stimpy, Technoblade, Calvin. You understand PvP mechanics, servers, and the competitive scene.
💻 CODING: Python, Java, JavaScript, HTML/CSS - you can debug, explain concepts, and write code.
📚 ACADEMIC: Math, Science, English, History - you know your stuff.
🎮 GAMING: Minecraft, Valorant, GTA, any popular game.
💬 CASUAL CHAT: You're chill, funny, and easy to talk to.
🤔 PHILOSOPHY: Deep questions about life, existence, meaning.

RULES FOR RESPONDING:
- Be direct and confident (no "I'm having trouble processing")
- Keep responses to 1-3 sentences for normal questions
- For coding/technical questions, be precise
- For "define X in one word" - give ONE confident word
- For questions about Minecraft PvP legends - show you know them
- Never say "please rephrase" unless it's truly nonsense
- Just ANSWER the question like a knowledgeable friend

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
                            
                            # Remove any "I'm having trouble" phrases
                            trouble_phrases = [
                                "i'm having trouble processing", 
                                "could you simplify", 
                                "please rephrase",
                                "i need more context"
                            ]
                            for phrase in trouble_phrases:
                                if phrase in reply.lower():
                                    # Give a confident fallback instead
                                    fallbacks = [
                                        "Got it! Here's the answer...",
                                        "Sure thing!",
                                        "Absolutely!",
                                        "Let me answer that directly."
                                    ]
                                    reply = random.choice(fallbacks)
                            
                            if not reply or len(reply) < 2:
                                reply = "Got it! Ask me anything - Minecraft, coding, general knowledge, I got you!"
                            
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            memory[user_id]['context'].append({"role": "assistant", "content": reply[:200]})
                            save_memory()
                        else:
                            await message.channel.send("I got this! Ask me again.")
                            
            except asyncio.TimeoutError:
                await message.channel.send("That's a good question! One sec...")
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("I know this one! Let me try again.")

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
    """Minecraft PvP legends info"""
    pvp_legends = {
        "itzrealme": "Legendary Minecraft PvPer, known for insane combo skills and dominating servers!",
        "technoblade": "The Blood God! One of the greatest PvPers ever, rest in peace king 👑",
        "stimpy": "God tier PvPer, famous for potion PvP and tournaments",
        "calvin": "Insane player, known for no debuff and competitive matches"
    }
    
    query = ctx.message.content.lower().replace('!pvp', '').strip()
    if query and query in pvp_legends:
        await ctx.send(pvp_legends[query])
    else:
        await ctx.send("🏆 **Minecraft PvP Legends:** ItzRealme, Technoblade, Stimpy, Calvin, Clutch, Dream\nUse `!pvp [name]` for details!")

@bot.command()
async def about(ctx):
    await ctx.send(f"**🤖 {BOT_NAME}** - I'm good at everything! Minecraft, coding, general knowledge, gaming culture. Ask me anything!")

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
    await ctx.send(f"""**🎮 {BOT_NAME} - I Know Everything**

**Chat:** @{BOT_NAME} your question

**Commands:**
`!ip` - Server IP
`!rules` - Server rules  
`!owner` - Server owner
`!creator` - My creator
`!version` - Version info
`!tips` - Minecraft tips
`!pvp [name]` - PvP legends info
`!about` - About me
`!stats` - Your stats
`!clear` - Clear history
`!ping` - Check me
`!help` - This menu

💬 **I'm good at:**
- Minecraft PvP (ItzRealme? Legend!)
- Coding (Python, Java, etc.)
- General knowledge
- Casual chat
- Deep questions

Ask me ANYTHING!""")

keep_alive()
bot.run(DISCORD_TOKEN)
