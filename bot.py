import discord
from discord.ext import commands
import aiohttp
import re
import json
import os
import random
import urllib.parse
import asyncio
from datetime import datetime
from collections import defaultdict
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
BOT_VERSION = "3.0.0"

# REPLACE WITH YOUR ACTUAL DISCORD USER ID
OWNER_DISCORD_ID = 123456789012345678  # CHANGE THIS NUMBER!

MEMORY_FILE = 'zx_memory.json'
USER_PROFILES_FILE = 'user_profiles.json'
SENTIMENT_LOG_FILE = 'sentiment_log.json'

# ========== BOT PERSONALITY (Fixed - added missing key) ==========
BOT_PERSONALITY = {
    "greetings": [
        "Heyyy {}! What's crackin'? 🔥",
        "Ayo {}! Ready to game? 🎮",
        "Sup {}! Your favorite AI is here! 💀",
        "{}! Long time no see! Miss me? 😏",
        "Yo yo yo {}! Let's gooo! 🚀"
    ],
    "compliments": [
        "You're actually goated fr fr 🐐",
        "Bruh your vibes are immaculate ✨",
        "Ngl you're pretty cool 😎",
        "You built different fr 💪",
        "That's a W take my guy 🏆"
    ],
    "sarcastic": [
        "Oh wow, SO original 🙄",
        "Bruh... really? 💀",
        "That's crazy... but I don't remember asking 😭",
        "Tell me you're new without telling me you're new 🗿",
        "Aight bet, whatever you say chief 👑"
    ],
    "excited": [
        "LETS GOOOO! 🚀",
        "AYO THAT'S WILD! 🔥",
        "NO CAP? THAT'S INSANE! 😭",
        "SHEEEESH! 🥶",
        "BET THAT UP! 💯"
    ],
    # FIXED: Added the missing key
    "minecraft_activities": [
        "build a mega base",
        "hunt for ancient debris",
        "fight the Ender Dragon",
        "create a redstone computer",
        "collect every mob head",
        "build a fully automated farm",
        "explore a woodland mansion",
        "complete all advancements"
    ],
    "emojis": ["🎮", "🔥", "💀", "👀", "🤔", "😭", "🗿", "💯", "🥶", "🐐", "⚔️", "👑"]
}

# ========== SIMPLE SENTIMENT ANALYSIS (No TextBlob needed) ==========
def analyze_sentiment(text):
    """Simple but effective sentiment analysis without external libraries"""
    text_lower = text.lower()
    
    # Positive keywords
    positive_words = [
        "good", "great", "awesome", "amazing", "love", "like", "happy", "excited", 
        "fun", "best", "cool", "nice", "perfect", "wonderful", "fantastic", "lit",
        "hype", "let's go", "letgo", "pog", "poggers", "goated", "goat"
    ]
    
    # Negative keywords
    negative_words = [
        "bad", "terrible", "awful", "hate", "sad", "angry", "mad", "upset", "annoying",
        "stupid", "dumb", "trash", "garbage", "worst", "sucks", "unlucky", "bruh",
        "depressed", "pain", "suffering"
    ]
    
    # Excitement indicators
    excitement_indicators = ["!!!", "let's go", "letsgo", "hype", "wooo", "letsgooo", "lesgo", "lessgo"]
    
    # Calculate scores
    positive_score = sum(1 for word in positive_words if word in text_lower)
    negative_score = sum(1 for word in negative_words if word in text_lower)
    
    # Check for excitement
    is_excited = any(excitement in text_lower for excitement in excitement_indicators) or text.endswith("!!!")
    
    # Determine mood
    if is_excited or (positive_score >= 2 and "!" in text):
        mood = "excited"
        emoji = "🤩🔥"
        polarity = 0.8
    elif positive_score > negative_score:
        mood = "happy"
        emoji = "😊"
        polarity = 0.4
    elif negative_score > positive_score:
        if "angry" in text_lower or "mad" in text_lower or "hate" in text_lower:
            mood = "angry"
            emoji = "😠"
            polarity = -0.7
        else:
            mood = "sad"
            emoji = "😔"
            polarity = -0.5
    else:
        mood = "neutral"
        emoji = "😐"
        polarity = 0
    
    return {
        "polarity": polarity,
        "mood": mood,
        "emoji": emoji,
        "is_positive": polarity > 0,
        "is_negative": polarity < 0,
        "intensity": abs(polarity)
    }

def get_empathetic_response(sentiment, user_name):
    """Generate response based on user's sentiment"""
    if sentiment["mood"] == "excited":
        return f"AYOO {user_name} I'M HYPE WITH YOU! {random.choice(BOT_PERSONALITY['excited'])}"
    elif sentiment["mood"] == "happy":
        return f"Love the positive energy {user_name}! {random.choice(BOT_PERSONALITY['compliments'])}"
    elif sentiment["mood"] == "sad":
        return f"Aye {user_name}, you good? 😔 Want to talk about it or play some MC to cheer up? I gotchu 💙"
    elif sentiment["mood"] == "angry":
        return f"Bruh {user_name}, take a deep breath! 🧘 Nothing's that serious fr. Want some Minecraft therapy? 🎮"
    else:
        return None

# ========== ENHANCED MEMORY STRUCTURE ==========
if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, 'r') as f:
        memory = json.load(f)
else:
    memory = {}

if os.path.exists(USER_PROFILES_FILE):
    with open(USER_PROFILES_FILE, 'r') as f:
        user_profiles = json.load(f)
else:
    user_profiles = {}

if os.path.exists(SENTIMENT_LOG_FILE):
    with open(SENTIMENT_LOG_FILE, 'r') as f:
        sentiment_log = json.load(f)
else:
    sentiment_log = {}

def save_all_data():
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
        with open(USER_PROFILES_FILE, 'w') as f:
            json.dump(user_profiles, f, indent=2)
        with open(SENTIMENT_LOG_FILE, 'w') as f:
            json.dump(sentiment_log, f, indent=2)
    except Exception as e:
        print(f"Save error: {e}")

# ========== USER PROFILE MANAGEMENT ==========
def update_user_profile(user_id, user_name, message_content, sentiment):
    """Track user stats, preferences, and behavior patterns"""
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "name": user_name,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "total_messages": 0,
            "total_interactions": 0,
            "mood_tracker": [],
            "favorite_topics": {},
            "personality": {
                "avg_sentiment": 0,
                "talkativeness": 0
            },
            "trust_level": 0.5,
            "achievements": []
        }
    
    profile = user_profiles[user_id]
    profile["name"] = user_name
    profile["last_seen"] = datetime.now().isoformat()
    profile["total_messages"] += 1
    profile["total_interactions"] += 1
    
    # Track mood history (keep last 20)
    profile["mood_tracker"].append({
        "timestamp": datetime.now().isoformat(),
        "mood": sentiment["mood"],
        "polarity": sentiment["polarity"]
    })
    if len(profile["mood_tracker"]) > 20:
        profile["mood_tracker"] = profile["mood_tracker"][-20:]
    
    # Update average sentiment
    moods = [m["polarity"] for m in profile["mood_tracker"]]
    profile["personality"]["avg_sentiment"] = sum(moods) / len(moods) if moods else 0
    
    # Detect topics from message
    topics = ["minecraft", "pvp", "build", "redstone", "server", "mod", "potion", "enchant", "diamond", "nether", "ender", "creeper"]
    for topic in topics:
        if topic in message_content.lower():
            profile["favorite_topics"][topic] = profile["favorite_topics"].get(topic, 0) + 1
    
    # Update trust level based on positive interactions
    if sentiment["is_positive"]:
        profile["trust_level"] = min(1.0, profile["trust_level"] + 0.02)
    elif sentiment["is_negative"]:
        profile["trust_level"] = max(0, profile["trust_level"] - 0.01)
    
    # Check for achievements
    if profile["total_messages"] >= 100 and "100_messages" not in profile["achievements"]:
        profile["achievements"].append("100_messages")
    if profile["trust_level"] >= 0.8 and "trusted_friend" not in profile["achievements"]:
        profile["achievements"].append("trusted_friend")
    if profile["total_messages"] >= 500 and "OG" not in profile["achievements"]:
        profile["achievements"].append("OG")
    
    save_all_data()
    return profile

# ========== HARDCODED RESPONSES ==========
HARDCODED_RESPONSES = {
    "who created you": f"I was created by **{CREATOR_NAME}**! He built me for ZX Servers. 🎮",
    "who made you": f"**{CREATOR_NAME}** made me!",
    "your creator": f"My creator is **{CREATOR_NAME}**!",
    "what is your name": f"I'm **{BOT_NAME}**, your ZX Servers AI assistant!",
    "who are you": f"I'm **{BOT_NAME}**, created by {CREATOR_NAME} for {SERVER_NAME}!",
    "itzrealme": "**ItzRealme** is a LEGENDARY Minecraft PvPer! Absolute beast! 🏆",
    "technoblade": "**Technoblade** - The Blood God! Rest in peace, king. 👑",
    "server ip": f"🎮 **{SERVER_NAME} IP:** `{SERVER_IP}` | {SERVER_VERSION} {SERVER_TYPE}",
    "i'm bored": f"BET! Let me give you something to do: {random.choice(BOT_PERSONALITY['minecraft_activities'])}! 🔥",
    "i love you": "Ayo? 😳 I'm flattered but I'm just an AI. Let's keep it Minecraft, bestie! 💀",
    "i'm sad": "Aye come here 🫂 Minecraft always cheers me up. Want to play together? 💙",
}

# ========== AI RESPONSE GENERATION ==========
async def get_ai_response(prompt, user_id, user_name, sentiment):
    """Enhanced AI with context and personality"""
    
    # Get user profile for personalization
    profile = user_profiles.get(user_id, {})
    fav_topics = profile.get("favorite_topics", {})
    top_topic = max(fav_topics, key=fav_topics.get, default="minecraft") if fav_topics else "minecraft"
    
    # Build personality injection
    personality_prompt = f"""You are {BOT_NAME}, a super friendly, witty, and intelligent AI assistant for {SERVER_NAME}.
    
Your personality:
- Use modern slang naturally (no cap, bet, fr, sheesh, ayo, bruh)
- Be genuinely helpful but keep it casual
- Use emojis occasionally
- Reference Minecraft and gaming culture
- Keep responses 1-2 sentences

Context:
- User: {user_name} (trust level: {profile.get('trust_level', 0.5)})
- Their mood: {sentiment['mood']} {sentiment['emoji']}
- Their favorite topic: {top_topic}

User says: {prompt}

Reply briefly and naturally:"""
    
    try:
        async with aiohttp.ClientSession() as session:
            encoded = urllib.parse.quote(personality_prompt[:1000])
            url = f"https://text.pollinations.ai/{encoded}"
            
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    reply = await resp.text()
                    reply = reply.strip()
                    
                    if len(reply) < 2:
                        reply = f"Got you {user_name}! What else you got? 🔥"
                    
                    if len(reply) > 1900:
                        reply = reply[:1900] + "..."
                    
                    return reply
                else:
                    return f"My bad {user_name}, AI is acting up! Try again? 🔄"
                    
    except asyncio.TimeoutError:
        return f"Ayo {user_name}, the AI servers are lagging! Give me 2 seconds and try again? ⏰"
    except Exception as e:
        print(f"AI Error: {e}")
        return f"Bruh {user_name}, something broke {random.choice(['💀', '😭', '🗿'])} Try again!"

# ========== DISCORD BOT SETUP ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, reconnect=True)

def clean_mentions(content, bot_id):
    content = re.sub(f'<@!?{bot_id}>', '', content)
    return content.strip()

async def set_bot_status():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{SERVER_NAME} | {SERVER_VERSION}"),
        status=discord.Status.online
    )

@bot.event
async def on_ready():
    await set_bot_status()
    print(f'✅ {BOT_NAME} v{BOT_VERSION} online! | Created by {CREATOR_NAME}')
    print(f'📊 Loaded {len(user_profiles)} user profiles | {len(memory)} conversation threads')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        user_name = message.author.name
        clean_content = clean_mentions(message.content, bot.user.id)
        
        if not clean_content:
            await message.channel.send(random.choice(BOT_PERSONALITY["greetings"]).format(user_name))
            return
        
        # Analyze sentiment
        sentiment = analyze_sentiment(clean_content)
        
        # Update user profile
        profile = update_user_profile(user_id, user_name, clean_content, sentiment)
        
        # Log sentiment
        if user_id not in sentiment_log:
            sentiment_log[user_id] = []
        sentiment_log[user_id].append({
            "timestamp": datetime.now().isoformat(),
            "message": clean_content[:100],
            "sentiment": sentiment["mood"],
            "polarity": sentiment["polarity"]
        })
        if len(sentiment_log[user_id]) > 50:
            sentiment_log[user_id] = sentiment_log[user_id][-50:]
        save_all_data()
        
        # Initialize memory for user
        if user_id not in memory:
            memory[user_id] = {'context': []}
        
        # Check for empathetic response based on sentiment
        empathetic_response = get_empathetic_response(sentiment, user_name)
        if empathetic_response and sentiment["intensity"] > 0.4:
            await message.channel.send(empathetic_response)
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            memory[user_id]['context'].append({"role": "assistant", "content": empathetic_response})
            save_all_data()
            return
        
        # Check hardcoded responses
        lower_content = clean_content.lower()
        for key, response in HARDCODED_RESPONSES.items():
            if key in lower_content:
                await message.channel.send(response)
                memory[user_id]['context'].append({"role": "user", "content": clean_content})
                memory[user_id]['context'].append({"role": "assistant", "content": response})
                save_all_data()
                return
        
        # Get AI response with full context
        async with message.channel.typing():
            # Store message
            memory[user_id]['context'].append({"role": "user", "content": clean_content[:500]})
            if len(memory[user_id]['context']) > 20:
                memory[user_id]['context'] = memory[user_id]['context'][-20:]
            
            # Get AI response
            reply = await get_ai_response(clean_content, user_id, user_name, sentiment)
            
            await message.channel.send(reply)
            memory[user_id]['context'].append({"role": "assistant", "content": reply[:300]})
            save_all_data()
    
    await bot.process_commands(message)

# ========== COMMANDS ==========

@bot.command()
async def profile(ctx):
    """View your personal profile and stats"""
    user_id = str(ctx.author.id)
    if user_id in user_profiles:
        p = user_profiles[user_id]
        embed = discord.Embed(title=f"📊 {ctx.author.name}'s Profile", color=0x00ff00)
        embed.add_field(name="First Seen", value=p.get('first_seen', 'Unknown')[:10], inline=True)
        embed.add_field(name="Messages", value=p.get('total_messages', 0), inline=True)
        embed.add_field(name="Trust Level", value=f"{p.get('trust_level', 0.5)*100:.0f}%", inline=True)
        
        if p.get('mood_tracker'):
            avg_mood = p.get('personality', {}).get('avg_sentiment', 0)
            mood_emoji = "😊" if avg_mood > 0 else "😐" if avg_mood > -0.2 else "😔"
            embed.add_field(name="Avg Mood", value=f"{mood_emoji} {avg_mood:+.2f}", inline=True)
        
        if p.get('achievements'):
            embed.add_field(name="Achievements", value=", ".join(p['achievements'][:3]), inline=False)
        
        if p.get('favorite_topics'):
            top = sorted(p['favorite_topics'].items(), key=lambda x: x[1], reverse=True)[:3]
            fav = ", ".join([t[0] for t in top])
            embed.add_field(name="Interests", value=fav, inline=False)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"No profile yet! Just talk to me and I'll learn about you {ctx.author.name}! 🎮")

@bot.command()
async def mood(ctx):
    """Check your recent mood trends"""
    user_id = str(ctx.author.id)
    if user_id in sentiment_log and sentiment_log[user_id]:
        recent = sentiment_log[user_id][-10:]
        moods = [s['sentiment'] for s in recent]
        mood_counts = {m: moods.count(m) for m in set(moods)}
        
        result = f"**{ctx.author.name}'s Recent Mood** 📊\n"
        for mood, count in mood_counts.items():
            emoji = {"happy": "😊", "sad": "😔", "angry": "😠", "excited": "🤩", "neutral": "😐"}.get(mood, "😐")
            result += f"{emoji} {mood}: {count} times\n"
        
        latest = sentiment_log[user_id][-1]
        result += f"\nLast mood: {latest['sentiment']}"
        await ctx.send(result)
    else:
        await ctx.send(f"Not enough data yet! Chat with me more and I'll track your vibes {ctx.author.name}! 🎭")

@bot.command()
async def stats(ctx):
    """Your conversation stats with me"""
    user_id = str(ctx.author.id)
    if user_id in memory:
        count = len(memory[user_id].get('context', [])) // 2
        await ctx.send(f"📊 {ctx.author.name}, we've had {count} conversations! That's {count} W's in my book! 🏆")
    else:
        await ctx.send(f"No history yet! Say something to me {ctx.author.name}! 🎮")

@bot.command()
async def clear(ctx):
    """Clear YOUR conversation history"""
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': []}
        save_all_data()
        await ctx.send(f"✅ Cleared our chat history {ctx.author.name}! Want to start fresh? 🔄")
    else:
        await ctx.send("No history to clear! We haven't talked yet! 👋")

@bot.command()
async def reset(ctx):
    """⚠️ RESET ALL MEMORY for EVERYONE (Owner only)"""
    if ctx.author.id == OWNER_DISCORD_ID:
        global memory, user_profiles, sentiment_log
        memory = {}
        user_profiles = {}
        sentiment_log = {}
        save_all_data()
        await ctx.send("✅ **FULL RESET COMPLETE!** All conversation memory, profiles, and sentiment data cleared.")
        print(f"⚠️ Complete reset by {ctx.author.name} (ID: {ctx.author.id})")
    else:
        await ctx.send("❌ Only the server owner can use this command! Nice try though 💀")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    if latency < 50:
        msg = f"Pong! 🏓 {latency}ms - Lightning fast! ⚡"
    elif latency < 150:
        msg = f"Pong! 🏓 {latency}ms - Solid! 🎮"
    else:
        msg = f"Pong! 🏓 {latency}ms - Bit laggy, but we ball 💀"
    await ctx.send(msg)

@bot.command()
async def ip(ctx):
    await ctx.send(f"🎮 **{SERVER_NAME} IP:** `{SERVER_IP}` | {SERVER_VERSION} {SERVER_TYPE}\nCome play, no cap! 🔥")

@bot.command()
async def rules(ctx):
    await ctx.send(f"**📜 {SERVER_NAME} Rules:**\n1️⃣ Be cool, don't be uncool\n2️⃣ No griefing (unless it's funny)\n3️⃣ No hacking (skill issue if you do)\n4️⃣ HAVE FUN! 🎮")

@bot.command()
async def owner(ctx):
    await ctx.send(f"👑 **Server Owner:** {OWNER}\nHe's the goat fr! Show some respect! 🐐")

@bot.command()
async def creator(ctx):
    await ctx.send(f"🤖 **My Creator:** {CREATOR_NAME}\nAbsolute legend coded me with love and caffeine! ☕")

@bot.command()
async def version(ctx):
    await ctx.send(f"📦 **{SERVER_NAME}:** {SERVER_VERSION} | 🤖 **{BOT_NAME}:** {BOT_VERSION}\nWe stay updated fr! 🔄")

@bot.command()
async def tips(ctx):
    tips = [
        "💎 Diamonds at Y=11-12 in 1.12.2!",
        "🏠 Pro builder tip: Use stairs + slabs for DETAILS!",
        "🌾 Water hydrates 4 blocks in each direction!",
        "⚔️ PvP hack: W-tap to reset sprint and deal more knockback!",
        "📚 15 bookshelves = max level 30 enchants!",
        "🔥 Want ancient debris? Bed mining at Y=15 in Nether!",
        "🐉 The Ender Dragon? More like the Ender L-taker!",
        "🎯 Crossbows with fireworks = best crowd control!"
    ]
    await ctx.send(f"{random.choice(tips)}\n\nWant more? Just ask me! 🔥")

@bot.command()
async def pvp(ctx):
    await ctx.send(f"🏆 **Minecraft PvP Legends:**\n• **ItzRealme** - The GOAT of {SERVER_NAME}\n• **Technoblade** - The Blood God (o7)\n• **Dream** - Manhunt legend\n• **Stimpy** - Movement god\n\nAsk me about any of them! ⚔️")

@bot.command()
async def about(ctx):
    embed = discord.Embed(title=f"🤖 About {BOT_NAME}", color=0x9b59b6)
    embed.description = f"I'm an AI assistant with **sentiment analysis**, **user memory**, and **personality**!\n\nCreated by **{CREATOR_NAME}** for **{SERVER_NAME}**"
    embed.add_field(name="🧠 Features", value="• Sentiment analysis\n• User profiles\n• Mood tracking\n• Personalized responses", inline=False)
    embed.add_field(name="📊 Stats", value=f"• Tracking {len(user_profiles)} users\n• {sum(len(m.get('context', [])) for m in memory.values())//2} conversations", inline=False)
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | Made with 💀 and ☕")
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title=f"🎮 {BOT_NAME} - Commands Menu", color=0x3498db)
    embed.description = f"Hey {ctx.author.name}! Here's what I can do:\n\n**💬 Chat with me:** `@{BOT_NAME} your message`"
    
    embed.add_field(name="📊 Profile Commands", value="`!profile` - Your stats\n`!mood` - Your mood history\n`!stats` - Chat stats\n`!clear` - Clear history", inline=False)
    embed.add_field(name="🎮 Minecraft", value="`!ip` - Server IP\n`!tips` - Pro tips\n`!pvp` - PvP legends\n`!rules` - Server rules", inline=False)
    embed.add_field(name="🤖 Bot Info", value="`!about` - About me\n`!owner` - Server owner\n`!creator` - My creator\n`!version` - Version info\n`!ping` - Latency check\n`!help` - This menu", inline=False)
    
    embed.add_field(name="🔒 Owner Only", value="`!reset` - Reset ALL memory", inline=False)
    embed.add_field(name="✨ Features", value="• Sentiment analysis (I know how you feel)\n• Memory (I remember you)\n• Personalized responses", inline=False)
    embed.set_footer(text=f"Try mentioning me! @{BOT_NAME} What's up?")
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Bruh that command doesn't exist 💀 Try `!help` to see what I can do!")
    else:
        print(f"Error: {error}")
        await ctx.send(f"Ayo {ctx.author.name}, something broke! {random.choice(['Try again?', 'My bad fr', 'Say that one more time'])} 🔄")

# ========== START BOT ==========
keep_alive()
bot.run(DISCORD_TOKEN)
