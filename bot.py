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
# Change these to customize your bot's status
STATUS_TYPE = "watching"  # Options: "playing", "watching", "listening", "streaming"
STATUS_TEXT = f"{SERVER_NAME} | {SERVER_VERSION}"  # Status message
STATUS_DND = True  # Set to True for Do Not Disturb, False for online
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
    # Set status (Do Not Disturb or Online)
    if STATUS_DND:
        status = discord.Status.dnd
    else:
        status = discord.Status.online
    
    # Set activity based on STATUS_TYPE
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
    # Set custom status
    await set_bot_status()
    
    print(f'✅ {BOT_NAME} is online!')
    print(f'👨‍💻 Created by: {CREATOR_NAME}')
    print(f'🎮 Serving {SERVER_NAME} - {SERVER_VERSION} {SERVER_TYPE}')
    print(f'📊 Status: {STATUS_TYPE} "{STATUS_TEXT}"')
    print(f'🔕 Do Not Disturb: {STATUS_DND}')
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
            
            # Get conversation context
            context = memory[user_id]['context'][-8:]
            context_text = ""
            if context:
                for msg in context[-6:]:
                    context_text += f"{'User' if msg['role'] == 'user' else BOT_NAME}: {msg['content']}\n"
            
            # Store user message
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            
            # Keep memory limited
            if len(memory[user_id]['context']) > 20:
                memory[user_id]['context'] = memory[user_id]['context'][-20:]
            
            # Build professional prompt
            prompt = f"""You are {BOT_NAME}, an AI assistant for {SERVER_NAME} Minecraft server.

About you:
- Name: {BOT_NAME}
- Creator: {CREATOR_NAME}
- Server: {SERVER_NAME} (Minecraft {SERVER_VERSION} {SERVER_TYPE})

{context_text}User ({message.author.name}) asks: {clean_content}

Guidelines:
- Be helpful, polite, and professional
- Answer questions directly and accurately
- Keep responses concise (1-3 sentences)
- If asked about Minecraft 1.12.2, provide specific tips
- For general questions, give clear answers
- Always be respectful

Your response:"""
            
            try:
                async with aiohttp.ClientSession() as session:
                    encoded_prompt = urllib.parse.quote(prompt)
                    url = f"https://text.pollinations.ai/{encoded_prompt}"
                    
                    async with session.get(url, timeout=30) as resp:
                        if resp.status == 200:
                            reply = await resp.text()
                            reply = reply.strip()
                            
                            # Clean up any JSON formatting
                            if reply.startswith('{'):
                                try:
                                    parsed = json.loads(reply)
                                    if 'content' in parsed:
                                        reply = parsed['content']
                                    elif 'choices' in parsed:
                                        reply = parsed['choices'][0].get('message', {}).get('content', str(reply))
                                except:
                                    # Remove JSON-like patterns
                                    reply = re.sub(r'\{[^{}]*\}', '', reply)
                                    reply = reply.strip()
                            
                            # Clean up escaped characters
                            reply = reply.replace('\\n', ' ').replace('\\"', '"')
                            
                            # Remove any "reasoning" text if present
                            if 'reasoning' in reply.lower():
                                # Extract just the response part
                                parts = reply.split('"content":"')
                                if len(parts) > 1:
                                    reply = parts[1].split('"')[0]
                            
                            # Fallback if empty
                            if not reply or len(reply) < 1:
                                reply = "I'm here to help! What would you like to know?"
                            
                            # Discord message limit
                            if len(reply) > 1900:
                                reply = reply[:1900] + "..."
                            
                            await message.channel.send(reply)
                            
                            # Store bot response in memory
                            memory[user_id]['context'].append({"role": "assistant", "content": reply})
                            save_memory()
                            
                        else:
                            await message.channel.send("I'm experiencing some technical difficulties. Please try again in a moment.")
                            
            except asyncio.TimeoutError:
                await message.channel.send("The request timed out. Please try again.")
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("An error occurred. Please try again.")
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def ip(ctx):
    """Get the server IP address"""
    await ctx.send(f"**{SERVER_NAME} IP Address:** `{SERVER_IP}`\n**Version:** {SERVER_VERSION} {SERVER_TYPE}")

@bot.command()
async def rules(ctx):
    """Display server rules"""
    rules_text = f"""**📜 {SERVER_NAME} Rules**

1. Be respectful to all players
2. No griefing or stealing
3. No hacking or exploiting
4. Have fun and help others

Contact {OWNER} for any issues."""
    await ctx.send(rules_text)

@bot.command()
async def owner(ctx):
    """Show server owner information"""
    await ctx.send(f"**Server Owner:** {OWNER}")

@bot.command()
async def creator(ctx):
    """Show who created the bot"""
    await ctx.send(f"**Bot Creator:** {CREATOR_NAME}")

@bot.command()
async def version(ctx):
    """Show server and bot versions"""
    await ctx.send(f"**Server Version:** {SERVER_VERSION} {SERVER_TYPE}\n**Bot Version:** {BOT_VERSION}")

@bot.command()
async def tips(ctx):
    """Get random Minecraft tips"""
    tips_list = [
        "💎 **Mining:** Diamonds generate most frequently at Y-level 11-12",
        "🏠 **Building:** Use stairs and slabs to add detail to your builds",
        "🌾 **Farming:** Water hydrates soil up to 4 blocks away",
        "⚔️ **Combat:** Critical hits are performed by hitting while falling",
        "📚 **Enchanting:** 15 bookshelves gives maximum level 30 enchantments",
        "🔥 **Nether:** Bring fire resistance potions or golden apples",
        "🐟 **Fishing:** Luck of the Sea enchantment improves loot quality",
        "🚂 **Redstone:** Repeaters can delay signals by 0.1-0.4 seconds"
    ]
    await ctx.send(random.choice(tips_list))

@bot.command()
async def about(ctx):
    """About this bot"""
    about_text = f"""**🤖 About {BOT_NAME}**

- **Name:** {BOT_NAME}
- **Creator:** {CREATOR_NAME}
- **Version:** {BOT_VERSION}
- **Purpose:** Assisting the {SERVER_NAME} community

I can answer questions about Minecraft, provide server information, and help with general knowledge. Just mention me with @{BOT_NAME} to start a conversation."""
    await ctx.send(about_text)

@bot.command()
async def stats(ctx):
    """View your conversation statistics"""
    user_id = str(ctx.author.id)
    if user_id in memory and 'context' in memory[user_id]:
        msg_count = len(memory[user_id]['context'])
        await ctx.send(f"📊 **{ctx.author.name}** - You've sent {msg_count} messages in our conversation.")
    else:
        await ctx.send(f"📊 **{ctx.author.name}** - No conversation history yet. Mention me with @{BOT_NAME} to start chatting!")

@bot.command()
async def clear(ctx):
    """Clear your conversation history"""
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_memory()
        await ctx.send(f"✅ Your conversation history has been cleared, {ctx.author.name}.")
    else:
        await ctx.send("No conversation history to clear.")

@bot.command()
async def ping(ctx):
    """Check if the bot is responsive"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! 🏓 Latency: {latency}ms")

@bot.command()
async def setstatus(ctx, status_type: str = None, *, text: str = None):
    """Change bot status (Owner only)"""
    if ctx.author.id != int(OWNER_ID) if 'OWNER_ID' in dir() else False:
        # You can add owner ID check here
        await ctx.send("This command is restricted to the server owner.")
        return
    
    # This is a placeholder - implement owner check properly
    await ctx.send("Status change feature coming soon!")

@bot.command()
async def help(ctx):
    """Show all available commands"""
    help_text = f"""**🎮 {BOT_NAME} - Help Menu**

**Chat with me:** Just mention @{BOT_NAME} followed by your question.

**Available Commands:**

`!ip` - Display server IP address
`!rules` - Show server rules
`!owner` - Show server owner
`!creator` - Show bot creator
`!version` - Show version information
`!tips` - Get random Minecraft tips
`!about` - Learn about this bot
`!stats` - View your conversation statistics
`!clear` - Clear your conversation history
`!ping` - Check bot responsiveness
`!help` - Show this help menu

**Server Information:**
- **Name:** {SERVER_NAME}
- **Version:** {SERVER_VERSION}
- **Mode:** {SERVER_TYPE}
- **IP:** {SERVER_IP}

Need help? Just mention me and ask!"""
    await ctx.send(help_text)

# Start the keep-alive server and run the bot
keep_alive()
bot.run(DISCORD_TOKEN)
