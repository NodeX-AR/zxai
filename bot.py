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

# Server Information
SERVER_NAME = "ZX Servers"
SERVER_VERSION = "1.12.2"
SERVER_TYPE = "Survival"
OWNER = "Aswanth R"

# Creator/Bot Information
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
    print(f'🎮 Serving {SERVER_NAME}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        
        if user_id not in memory:
            memory[user_id] = {'context': []}
        
        clean_content = clean_mentions(message.content, bot.user.id)
        
        # Handle just a mention with no text
        if not clean_content:
            casual_responses = [
                f"Hey {message.author.name}! What's up? 👋",
                f"Yo {message.author.name}! Need something? 🎮",
                f"Sup {message.author.name}! 😎",
                f"Hello {message.author.name}! How can I help? 💬"
            ]
            await message.channel.send(random.choice(casual_responses))
            return
        
        # Build conversation context from memory
        context = memory[user_id]['context'][-6:]  # Last 6 messages for context
        context_text = ""
        if context:
            context_text = "Previous conversation:\n"
            for msg in context:
                role = "User" if msg['role'] == 'user' else f"{BOT_NAME}"
                context_text += f"{role}: {msg['content']}\n"
            context_text += "\n"
        
        # Store user message
        memory[user_id]['context'].append({"role": "user", "content": clean_content})
        
        # Build prompt with personality
        prompt = f"""You are {BOT_NAME}, a cool, friendly AI assistant for {SERVER_NAME} Minecraft server.

Your personality: Chatty, helpful, funny when appropriate, and natural. You talk like a friend.

Info about you:
- Name: {BOT_NAME} (NOT "ZX Bot", just {BOT_NAME})
- Creator: {CREATOR_NAME}
- Server: {SERVER_NAME} (Minecraft 1.12.2 Survival)

{context_text}User ({message.author.name}) just said: "{clean_content}"

Important rules:
- Respond naturally, like you're chatting with a friend
- Keep responses short and punchy (1-3 sentences usually)
- Be helpful but don't over-explain
- NEVER output JSON, code, or raw API data
- Just give a clean text response
- Be conversational and fun

Your response:"""
        
        # Keep memory limited
        if len(memory[user_id]['context']) > 20:
            memory[user_id]['context'] = memory[user_id]['context'][-20:]
        
        try:
            async with message.channel.typing():
                async with aiohttp.ClientSession() as session:
                    encoded = urllib.parse.quote(prompt)
                    url = f"https://text.pollinations.ai/{encoded}"
                    
                    async with session.get(url, timeout=45) as resp:
                        if resp.status == 200:
                            raw = await resp.text()
                            
                            # Clean up response
                            reply = raw.strip()
                            
                            # Remove JSON if it appears
                            if reply.startswith('{') and '"content"' in reply:
                                try:
                                    import json as jsonlib
                                    parsed = jsonlib.loads(reply)
                                    if 'content' in parsed:
                                        reply = parsed['content']
                                    elif 'choices' in parsed:
                                        reply = parsed['choices'][0].get('message', {}).get('content', reply)
                                except:
                                    # If JSON parsing fails, try regex
                                    match = re.search(r'"content":"([^"]*)"', reply)
                                    if match:
                                        reply = match.group(1)
                            
                            # Remove reasoning_content garbage
                            if 'reasoning_content' in reply:
                                reply = reply.split('"content":"')[-1].split('"')[0] if '"content":"' in reply else "Hey! What's up?"
                            
                            # Final cleanup
                            reply = reply.replace('\\n', '\n').replace('\\"', '"')
                            reply = re.sub(r'\{[^{}]*\}', '', reply)
                            reply = reply.strip()
                            
                            # Fallback if empty
                            if not reply or len(reply) < 1:
                                reply = random.choice([
                                    "Haha, for sure!", 
                                    "Got it! 👍", 
                                    "Interesting! Tell me more.",
                                    "I see what you mean!"
                                ])
                            
                            # Discord limit
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            
                            # Store bot response
                            memory[user_id]['context'].append({"role": "assistant", "content": reply})
                            save_memory()
                            
                        else:
                            await message.channel.send("One sec, I'm thinking... 🤔")
                            
        except asyncio.TimeoutError:
            await message.channel.send("Taking too long! Try again?")
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("Something went wrong! Try again.")
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def ip(ctx):
    await ctx.send(f"🎮 **ZX Servers IP:** `{SERVER_IP}`\nVersion: {SERVER_VERSION} Survival")

@bot.command()
async def rules(ctx):
    await ctx.send(f"**📜 Server Rules:**\n1️⃣ Be respectful\n2️⃣ No griefing\n3️⃣ No hacking\n4️⃣ Have fun!")

@bot.command()
async def owner(ctx):
    await ctx.send(f"👑 **Server Owner:** {OWNER}")

@bot.command()
async def creator(ctx):
    await ctx.send(f"🤖 I was created by **{CREATOR_NAME}**! He's the owner of ZX Servers. 🎮")

@bot.command()
async def version(ctx):
    await ctx.send(f"📦 **ZX Servers** - {SERVER_VERSION} Survival\n🤖 {BOT_NAME} version: {BOT_VERSION}")

@bot.command()
async def tips(ctx):
    tips_list = [
        "💎 **Diamonds** = Y level 11-12!",
        "🏠 **Building** = Use stairs and slabs for detail!",
        "🌾 **Farming** = Water within 4 blocks!",
        "⚔️ **Combat** = Crit hits when falling!",
        "📚 **Enchanting** = 15 bookshelves = level 30!",
        "🔥 **Nether** = Bring fire resistance!",
        "🐟 **Fishing** = Luck of the Sea = better loot!"
    ]
    await ctx.send(random.choice(tips_list))

@bot.command()
async def about(ctx):
    await ctx.send(f"**🤖 About {BOT_NAME}:**\n• Name: {BOT_NAME}\n• Creator: {CREATOR_NAME}\n• Server: {SERVER_NAME}\n• I'm here to help and chat! Just mention me. 💬")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send(f"✅ Cleared our chat history, {ctx.author.name}!")
    else:
        await ctx.send("No chat history to clear!")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory and 'context' in memory[user_id]:
        msg_count = len(memory[user_id]['context'])
        await ctx.send(f"📊 {ctx.author.name}, we've had {msg_count} messages together!")
    else:
        await ctx.send(f"📊 No chat history yet! Mention @{BOT_NAME} to start chatting!")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓")

@bot.command()
async def bothelp(ctx):
    help_text = f"""**🎮 {BOT_NAME} - ZX Servers Assistant**

**Just mention me:** @{BOT_NAME} your message

**Commands:**
`!ip` - Server IP
`!rules` - Server rules  
`!owner` - Server owner
`!creator` - Who made me
`!about` - About me
`!version` - Version info
`!tips` - Minecraft tips
`!stats` - Your chat stats
`!clear` - Clear history
`!ping` - Check if I'm alive
`!bothelp` - This menu

💬 **I remember our conversation!** Ask follow-up questions naturally."""
    await ctx.send(help_text)

# Start the bot
keep_alive()
bot.run(DISCORD_TOKEN)
