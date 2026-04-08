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

# ========== STATUS CONFIGURATION ==========
STATUS_TYPE = "watching"  # Options: "playing", "watching", "listening", "streaming"
STATUS_TEXT = f"{SERVER_NAME} | {SERVER_VERSION}"
STATUS_DND = True
# ============================================

if not DISCORD_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, reconnect=True)

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
    """Remove bot mention from message"""
    content = re.sub(f'<@!?{bot_id}>', '', content)
    return content.strip()

async def set_bot_status():
    """Set the bot's presence and status"""
    if STATUS_DND:
        status = discord.Status.dnd
    else:
        status = discord.Status.online
    
    if STATUS_TYPE.lower() == "playing":
        activity = discord.Game(name=STATUS_TEXT)
    elif STATUS_TYPE.lower() == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=STATUS_TEXT)
    elif STATUS_TYPE.lower() == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=STATUS_TEXT)
    elif STATUS_TYPE.lower() == "streaming":
        activity = discord.Streaming(name=STATUS_TEXT, url="https://twitch.tv/example")
    else:
        activity = discord.Game(name=STATUS_TEXT)
    
    await bot.change_presence(status=status, activity=activity)

@bot.event
async def on_ready():
    await set_bot_status()
    
    print(f'✅ {BOT_NAME} is online!')
    print(f'👨‍💻 Created by: {CREATOR_NAME}')
    print(f'🎮 Serving {SERVER_NAME} - {SERVER_VERSION} {SERVER_TYPE}')
    print(f'💬 Bot is ready!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Only respond when mentioned or in DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        
        # Initialize user memory
        if user_id not in memory:
            memory[user_id] = {'context': []}
        
        # Clean the message
        clean_content = clean_mentions(message.content, bot.user.id)
        
        # Just mention with no text
        if not clean_content:
            responses = [
                f"Hello {message.author.name}! How can I help you today?",
                f"Hi {message.author.name}! Feel free to ask me anything.",
                f"Greetings {message.author.name}! I'm here to help."
            ]
            await message.channel.send(random.choice(responses))
            return
        
        # Show typing indicator
        async with message.channel.typing():
            
            # Get conversation context (shorter for complex questions)
            context = memory[user_id]['context'][-4:]
            context_text = ""
            if context:
                for msg in context[-3:]:
                    context_text += f"{'User' if msg['role'] == 'user' else BOT_NAME}: {msg['content'][:100]}\n"
            
            # Store user message
            memory[user_id]['context'].append({"role": "user", "content": clean_content[:500]})  # Limit storage
            
            # Keep memory limited
            if len(memory[user_id]['context']) > 15:
                memory[user_id]['context'] = memory[user_id]['context'][-15:]
            
            # Check if it's a code question
            is_code = "class" in clean_content or "def " in clean_content or "print(" in clean_content
            
            # Build prompt based on complexity
            if is_code and len(clean_content) > 200:
                # For long code questions, use a more focused prompt
                prompt = f"""You are {BOT_NAME}, a programming expert.

User asks: {clean_content[:800]}

Answer directly and accurately. If it's a Python code question, explain the output and why. Keep response under 3 sentences. Be precise."""
            else:
                prompt = f"""You are {BOT_NAME}, an AI assistant for {SERVER_NAME}.

Context: {context_text}
User ({message.author.name}): {clean_content}

Guidelines:
- Answer directly and accurately
- Keep response under 3 sentences
- For code questions, give the output and brief explanation
- Be helpful and professional

Response:"""
            
            try:
                async with aiohttp.ClientSession() as session:
                    encoded_prompt = urllib.parse.quote(prompt[:1000])  # Limit prompt length
                    url = f"https://text.pollinations.ai/{encoded_prompt}"
                    
                    async with session.get(url, timeout=45) as resp:  # Longer timeout for complex questions
                        if resp.status == 200:
                            reply = await resp.text()
                            reply = reply.strip()
                            
                            # Clean up JSON
                            if reply.startswith('{'):
                                try:
                                    parsed = json.loads(reply)
                                    reply = parsed.get('content', parsed.get('response', str(reply)))
                                except:
                                    reply = re.sub(r'\{[^{}]*\}', '', reply)
                            
                            reply = reply.replace('\\n', '\n').replace('\\"', '"')
                            
                            # Remove reasoning content
                            if 'reasoning_content' in reply:
                                lines = reply.split('\n')
                                clean_lines = [l for l in lines if 'reasoning' not in l.lower()]
                                reply = '\n'.join(clean_lines) if clean_lines else "Here's the answer to your question."
                            
                            # Fallback
                            if not reply or len(reply) < 2:
                                reply = "I understand your question. Let me help you with that."
                            
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            
                            # Store bot response
                            memory[user_id]['context'].append({"role": "assistant", "content": reply[:200]})
                            save_memory()
                            
                        else:
                            await message.channel.send("I'm having trouble processing that. Could you simplify the question?")
                            
            except asyncio.TimeoutError:
                await message.channel.send("This question is complex and taking too long. Could you break it down or simplify?")
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("I encountered an error processing your request. Please try again.")
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def ip(ctx):
    await ctx.send(f"**{SERVER_NAME} IP:** `{SERVER_IP}`\n**Version:** {SERVER_VERSION} {SERVER_TYPE}")

@bot.command()
async def rules(ctx):
    rules_text = f"""**📜 {SERVER_NAME} Rules**

1. Be respectful to all players
2. No griefing or stealing
3. No hacking or exploiting
4. Have fun and help others

Contact {OWNER} for any issues."""
    await ctx.send(rules_text)

@bot.command()
async def owner(ctx):
    await ctx.send(f"**Server Owner:** {OWNER}")

@bot.command()
async def creator(ctx):
    await ctx.send(f"**Bot Creator:** {CREATOR_NAME}")

@bot.command()
async def version(ctx):
    await ctx.send(f"**Server:** {SERVER_VERSION} {SERVER_TYPE}\n**Bot:** {BOT_VERSION}")

@bot.command()
async def tips(ctx):
    tips_list = [
        "💎 Diamonds at Y-level 11-12",
        "🏠 Use stairs and slabs for detailed builds",
        "🌾 Water hydrates soil up to 4 blocks away",
        "⚔️ Critical hits = jump + attack",
        "📚 15 bookshelves = level 30 enchantments",
        "🔥 Bring fire resistance to the Nether",
        "🐟 Luck of the Sea = better fishing loot"
    ]
    await ctx.send(random.choice(tips_list))

@bot.command()
async def about(ctx):
    await ctx.send(f"**🤖 {BOT_NAME}** - Minecraft server assistant\nCreated by {CREATOR_NAME}\nAsk me anything about Minecraft or general knowledge!")

@bot.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory and 'context' in memory[user_id]:
        msg_count = len(memory[user_id]['context'])
        await ctx.send(f"📊 **{ctx.author.name}** - {msg_count} messages in our conversation.")
    else:
        await ctx.send(f"📊 **{ctx.author.name}** - No conversation history yet.")

@bot.command()
async def clear(ctx):
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send(f"✅ Conversation history cleared, {ctx.author.name}.")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! 🏓 {latency}ms")

@bot.command()
async def help(ctx):
    help_text = f"""**🎮 {BOT_NAME} - Help**

**Chat:** @{BOT_NAME} your question

**Commands:**
`!ip` `!rules` `!owner` `!creator` `!version` `!tips` `!about` `!stats` `!clear` `!ping` `!help`

**Server:** {SERVER_NAME} ({SERVER_VERSION} {SERVER_TYPE})
**IP:** {SERVER_IP}"""
    await ctx.send(help_text)

keep_alive()
bot.run(DISCORD_TOKEN)
