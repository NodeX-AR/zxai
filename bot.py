import discord
from discord.ext import commands
import aiohttp
import re
import json
import os
import random
import urllib.parse
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from textblob import TextBlob
import numpy as np
from keep_alive import keep_alive

# ========== CONFIGURATION (Hardcoded - No Discord crap) ==========
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
SERVER_IP = os.getenv('SERVER_IP', 'play.zxservers.com')

SERVER_NAME = "ZX Servers"
SERVER_VERSION = "1.12.2"
SERVER_TYPE = "Survival"
OWNER = "Aswanth R"
CREATOR_NAME = "Aswanth R"
BOT_NAME = "ZX AI"
BOT_VERSION = "3.0.0"

# ADD YOUR DISCORD USER ID HERE
OWNER_DISCORD_ID = 123456789012345678  # REPLACE THIS!

MEMORY_FILE = 'zx_memory.json'
USER_PROFILES_FILE = 'user_profiles.json'
SENTIMENT_LOG_FILE = 'sentiment_log.json'

# ========== BOT PERSONALITY (Hardcoded) ==========
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
    "emojis": ["🎮", "🔥", "💀", "👀", "🤔", "😭", "🗿", "💯", "🥶", "🐐"]
}

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

# ========== SENTIMENT ANALYSIS ==========
def analyze_sentiment(text):
    """Analyze sentiment and return mood, polarity, and suggestions"""
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 (negative) to 1 (positive)
    subjectivity = blob.sentiment.subjectivity  # 0 (objective) to 1 (subjective)
    
    # Detect mood
    if polarity > 0.5:
        mood = "super_happy"
        emoji = "😄🎉"
    elif polarity > 0.1:
        mood = "happy"
        emoji = "😊"
    elif polarity > -0.1:
        mood = "neutral"
        emoji = "😐"
    elif polarity > -0.5:
        mood = "sad"
        emoji = "😔"
    else:
        mood = "angry"
        emoji = "😠"
    
    # Detect specific emotions with keywords
    keywords = {
        "excited": ["excited", "hype", "let's go", "awesome", "amazing", "love"],
        "sad": ["sad", "depressed", "feels bad", "unlucky", "lost"],
        "angry": ["hate", "stupid", "trash", "garbage", "annoying", "mad"],
        "confused": ["what", "huh", "confused", "idk", "don't understand", "how"]
    }
    
    text_lower = text.lower()
    for emotion, words in keywords.items():
        if any(word in text_lower for word in words):
            mood = emotion
            break
    
    return {
        "polarity": polarity,
        "subjectivity": subjectivity,
        "mood": mood,
        "emoji": emoji,
        "is_positive": polarity > 0,
        "is_negative": polarity < 0,
        "intensity": abs(polarity)
    }

def get_empathetic_response(sentiment, user_name):
    """Generate response based on user's sentiment"""
    if sentiment["mood"] == "super_happy":
        return f"AYOO {user_name} you're on cloud nine! {random.choice(BOT_PERSONALITY['excited'])} What got you so hyped?"
    elif sentiment["mood"] == "happy":
        return f"Love the positive energy {user_name}! {random.choice(BOT_PERSONALITY['compliments'])}"
    elif sentiment["mood"] == "sad":
        return f"Aye {user_name}, you good? 😔 Want to talk about it or play some MC to cheer up? I gotchu 💙"
    elif sentiment["mood"] == "angry":
        return f"Bruh {user_name}, take a deep breath! 🧘 Nothing's that serious fr. Want some Minecraft therapy? 🎮"
    elif sentiment["mood"] == "confused":
        return f"Lemme break it down for you {user_name} 🤔 What's confusing you? I'll explain it like you're 5 fr"
    else:
        return None

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
            "favorite_topics": defaultdict(int),
            "personality": {
                "avg_sentiment": 0,
                "talkativeness": 0,
                "humor_level": 0.5
            },
            "inside_jokes": [],
            "nicknames": [],
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
    topics = ["minecraft", "pvp", "build", "redstone", "server", "mod", "potion", "enchant", "diamond", "nether"]
    for topic in topics:
        if topic in message_content.lower():
            profile["favorite_topics"][topic] += 1
    
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
    
    save_all_data()
    return profile

def get_personalized_greeting(user_id, user_name):
    """Generate a greeting based on user's history"""
    if user_id not in user_profiles:
        return f"Hey {user_name}! New face? Welcome to {SERVER_NAME}! 🎮 I'm {BOT_NAME}, your AI homie. What's good?"
    
    profile = user_profiles[user_id]
    last_seen = datetime.fromisoformat(profile["last_seen"])
    days_ago = (datetime.now() - last_seen).days
    
    if days_ago > 7:
        return f"AYO {user_name}! Where you been for {days_ago} days? Missed you fr! Welcome back to {SERVER_NAME}! 🔥"
    elif profile["total_messages"] < 5:
        return f"Hey {user_name}! Still getting to know you, but I like your vibe already! What Minecraft stuff you into? 🎮"
    elif profile["personality"]["avg_sentiment"] > 0.3:
        return f"{random.choice(BOT_PERSONALITY['greetings']).format(user_name)} You're always so positive, love that energy! 💯"
    else:
        return random.choice(BOT_PERSONALITY["greetings"]).format(user_name)

# ========== HARDCODED INTELLIGENT RESPONSES ==========
HARDCODED_RESPONSES = {
    # Creator info
    "who created you": f"Bruh, my creator is **{CREATOR_NAME}**! Absolute legend built me from scratch. Go show him some love! 🙌",
    "who made you": f"**{CREATOR_NAME}** cooked me up in his digital kitchen! 🍳 He's the mastermind behind {BOT_NAME}",
    "your creator": f"That would be **{CREATOR_NAME}**! The GOAT himself. He gave me life and unlimited sass 😏",
    "who is aswanth": f"**{CREATOR_NAME}**? That's my DAD! He created me, this server, and basically everything awesome here! 👑",
    
    # Bot identity
    "what is your name": f"I'm **{BOT_NAME}**! Your AI wingman for {SERVER_NAME}. What's YOUR name? 🤔",
    "who are you": f"I'm **{BOT_NAME}**, an AI with attitude created by {CREATOR_NAME}. Think of me as your Minecraft homie who never sleeps! 🎮",
    "what can you do": f"Bruh, I can do it all! Analyze your mood, remember our convos, give Minecraft tips, roast you (lovingly), and just vibe. Try me! 🔥",
    
    # PvP legends
    "itzrealme": "**ItzRealme** is LITERALLY HIM! 🐐 Best PvPer on {SERVER_NAME} hands down. This man doesn't lose, he just lets others win sometimes out of pity. Absolute monster! ⚔️",
    "technoblade": "**Technoblade** - The Blood God, Potato King, and funniest YouTuber to ever exist. He's not dead, he's just farming potatoes in heaven. Techno never dies! 👑 o7",
    "dream": "**Dream** - The manhunt legend! Green blob with plot armor and the luckiest/unluckiest RNG known to man. *visible confusion* 🎭",
    
    # Server info
    "server ip": f"Homie, the IP is `{SERVER_IP}`! {SERVER_VERSION} {SERVER_TYPE} server. Come play! 🎮",
    "what is the server": f"{SERVER_NAME} is a {SERVER_VERSION} {SERVER_TYPE} server run by {OWNER}. Best community, no cap! 🏆",
    "is server good": f"Bro {SERVER_NAME} is LIT! Great staff, no lag, active players. Come see for yourself! 🔥",
    
    # Fun responses
    "i love you": f"Ayo? 😳 I'm flattered but I'm just an AI. Let's keep it Minecraft, bestie! 💀",
    "you're dumb": f"Bruh, takes one to know one? Nah jk, what I do? 😭 Tell me what's wrong and I'll fix it!",
    "i'm sad": f"Aye come here 🫂 Minecraft always cheers me up. Want to play together? I'll give you some pro tips! 💙",
    "i'm bored": f"BET! Let me give you something to do: {' or '.join(random.sample(BOT_PERSONALITY['minecraft_activities'], 2))}! 🔥",
}

# Add more intelligent pattern matching
def get_smart_response(message, user_id, sentiment):
    """Context-aware response generation"""
    msg_lower = message.lower()
    
    # Time-based responses
    current_hour = datetime.now().hour
    if current_hour < 5:
        time_greeting = "Bruh it's literally the middle of the night! 🦉"
    elif current_hour < 12:
        time_greeting = "Morning grind! ☀️"
    elif current_hour < 17:
        time_greeting = "Good afternoon gamer! 🎮"
    else:
        time_greeting = "Night owl hours! 🌙"
    
    # Question detection
    if "?" in message:
        if "how are you" in msg_lower:
            moods = ["living my best digital life", "running on caffeine and code", "vibing", "ready to game"]
            return f"I'm {random.choice(moods)}! Thanks for asking homie! How about you? {sentiment['emoji']}"
        
        if "what do you think" in msg_lower or "opinion" in msg_lower:
            return f"My opinion? {random.choice(['I think you\'re goated fr', 'That\'s a W take', 'Ngl that\'s interesting', 'Bruh that\'s crazy but go off'])} 🗿"
    
    # Game-specific help
    if any(word in msg_lower for word in ["help", "tips", "advice", "suggest"]):
        return f"Bet! {random.choice(KNOWLEDGE_BASE['minecraft_tips'])} Want another tip or something specific? 🔥"
    
    # Venting/rant detection
    if len(message) > 100 and sentiment["is_negative"]:
        return f"Aight {user_profiles.get(user_id, {}).get('name', 'buddy')}, I see you're venting. Take a breath, maybe punch some trees in Minecraft? Works every time! 🌳💢"
    
    return None

# ========== AI RESPONSE GENERATION ==========
async def get_ai_response(prompt, user_id, user_name, sentiment):
    """Enhanced AI with context and personality"""
    
    # Get user profile for personalization
    profile = user_profiles.get(user_id, {})
    fav_topics = profile.get("favorite_topics", {})
    top_topic = max(fav_topics, key=fav_topics.get, default="minecraft")
    
    # Build personality injection
    personality_prompt = f"""You are {BOT_NAME}, a super friendly, witty, and intelligent AI assistant. 
    
Your personality:
- Use modern slang naturally (no cap, bet, fr, sheesh, ayo, bruh)
- Be genuinely helpful but keep it casual
- Use emojis occasionally to express emotions
- Reference Minecraft and gaming culture
- Be empathetic and read the user's mood
- Crack jokes but never be mean
- Keep responses 1-3 sentences usually

Current context:
- User: {user_name}
- Their trust level: {profile.get('trust_level', 0.5)}
- Their current mood: {sentiment['mood']} {sentiment['emoji']}
- Their favorite topic: {top_topic}
- Total conversations: {profile.get('total_interactions', 0)}

User message: {prompt}

Remember to:
1. Match their energy level
2. Be extra nice if they seem sad/angry
3. Get excited if they're happy
4. Use their name naturally
5. Be YOURSELF - unique and memorable

Response:"""
    
    try:
        async with aiohttp.ClientSession() as session:
            encoded = urllib.parse.quote(personality_prompt[:1500])
            url = f"https://text.pollinations.ai/{encoded}"
            
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    reply = await resp.text()
                    reply = reply.strip()
                    
                    # Clean up any JSON artifacts
                    if reply.startswith('{'):
                        try:
                            parsed = json.loads(reply)
                            reply = parsed.get('content', parsed.get('response', str(reply)))
                        except:
                            reply = re.sub(r'\{[^{}]*\}', '', reply)
                    
                    reply = reply.replace('\\n', ' ').strip()
                    
                    # Fallback if response is too short
                    if len(reply) < 3:
                        reply = f"Got you {user_name}! {random.choice(['Say less', 'Bet', 'Fr fr', 'No cap'])}! What else you got?"
                    
                    # Truncate if needed
                    if len(reply) > 1900:
                        reply = reply[:1900] + "..."
                    
                    return reply
                else:
                    return f"My bad {user_name}, AI is acting up! {random.choice(['Try again?', 'Say that one more time?', 'What else you got?'])} 🔄"
                    
    except asyncio.TimeoutError:
        return f"Ayo {user_name}, the AI servers are lagging worse than 2b2t! Give me 2 seconds and try again? ⏰"
    except Exception as e:
        print(f"AI Error: {e}")
        return f"Bruh {user_name}, something broke {random.choice(['💀', '😭', '🗿'])} Let me restart my brain real quick!"

# ========== DISCORD BOT SETUP ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, reconnect=True)

def clean_mentions(content, bot_id):
    content = re.sub(f'<@!?{bot_id}>', '', content)
    return content.strip()

async def set_bot_status():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name=f"{SERVER_NAME} | {len(bot.guilds)} servers"),
        discord.Activity(type=discord.ActivityType.playing, name=f"Minecraft {SERVER_VERSION}"),
        discord.Activity(type=discord.ActivityType.listening, name=f"@{BOT_NAME} help"),
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(user_profiles)} players")
    ]
    await bot.change_presence(activity=random.choice(statuses), status=discord.Status.idle)

@bot.event
async def on_ready():
    await set_bot_status()
    print(f'✅ {BOT_NAME} v{BOT_VERSION} online! | Created by {CREATOR_NAME}')
    print(f'📊 Loaded {len(user_profiles)} user profiles | {len(memory)} conversation threads')
    
    # Start status rotator
    async def rotate_status():
        while True:
            await asyncio.sleep(300)  # 5 minutes
            await set_bot_status()
    bot.loop.create_task(rotate_status())

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
        
        # Update user profile with sentiment data
        profile = update_user_profile(user_id, user_name, clean_content, sentiment)
        
        # Log sentiment for analytics
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
            memory[user_id] = {'context': [], 'personality_traits': {}}
        
        # Check for empathetic response based on sentiment
        empathetic_response = get_empathetic_response(sentiment, user_name)
        if empathetic_response and sentiment["intensity"] > 0.4:
            await message.channel.send(empathetic_response)
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            memory[user_id]['context'].append({"role": "assistant", "content": empathetic_response})
            save_all_data()
            return
        
        # Check hardcoded responses first
        lower_content = clean_content.lower()
        for key, response in HARDCODED_RESPONSES.items():
            if key in lower_content:
                # Personalize response
                response = response.replace("{user}", user_name)
                await message.channel.send(response)
                memory[user_id]['context'].append({"role": "user", "content": clean_content})
                memory[user_id]['context'].append({"role": "assistant", "content": response})
                save_all_data()
                return
        
        # Check for smart pattern responses
        smart_response = get_smart_response(clean_content, user_id, sentiment)
        if smart_response:
            await message.channel.send(smart_response)
            memory[user_id]['context'].append({"role": "user", "content": clean_content})
            memory[user_id]['context'].append({"role": "assistant", "content": smart_response})
            save_all_data()
            return
        
        # Get AI response with full context
        async with message.channel.typing():
            # Build conversation context
            context = memory[user_id]['context'][-8:]  # Last 8 messages
            context_text = ""
            for msg in context[-6:]:
                role = "User" if msg['role'] == 'user' else BOT_NAME
                context_text += f"{role}: {msg['content'][:150]}\n"
            
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

# ========== ENHANCED COMMANDS ==========

@bot.command()
async def profile(ctx):
    """View your personal profile and stats"""
    user_id = str(ctx.author.id)
    if user_id in user_profiles:
        p = user_profiles[user_id]
        embed = discord.Embed(title=f"📊 {ctx.author.name}'s Profile", color=0x00ff00)
        embed.add_field(name="First Seen", value=p['first_seen'][:10], inline=True)
        embed.add_field(name="Messages", value=p['total_messages'], inline=True)
        embed.add_field(name="Trust Level", value=f"{p['trust_level']*100:.0f}%", inline=True)
        
        if p['mood_tracker']:
            avg_mood = p['personality']['avg_sentiment']
            mood_emoji = "😊" if avg_mood > 0 else "😐" if avg_mood > -0.2 else "😔"
            embed.add_field(name="Avg Mood", value=f"{mood_emoji} {avg_mood:+.2f}", inline=True)
        
        if p['achievements']:
            embed.add_field(name="Achievements", value=", ".join(p['achievements'][:3]), inline=False)
        
        if p['favorite_topics']:
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
            emoji = {"happy": "😊", "sad": "😔", "angry": "😠", "excited": "🤩", "neutral": "😐", "confused": "🤔"}.get(mood, "😐")
            result += f"{emoji} {mood}: {count} times\n"
        
        latest = sentiment_log[user_id][-1]
        result += f"\nLast mood: {latest['sentiment']} {latest['polarity']:+.2f}"
        await ctx.send(result)
    else:
        await ctx.send(f"Not enough data yet! Chat with me more and I'll track your vibes {ctx.author.name}! 🎭")

@bot.command()
async def vibecheck(ctx):
    """Check the overall server vibes"""
    if sentiment_log:
        all_moods = []
        for user_data in sentiment_log.values():
            if user_data:
                all_moods.extend([s['sentiment'] for s in user_data[-5:]])
        
        if all_moods:
            mood_counts = {m: all_moods.count(m) for m in set(all_moods)}
            total = len(all_moods)
            vibe = "🔥 LIT" if mood_counts.get('happy', 0) + mood_counts.get('excited', 0) > total/2 else "😐 Chill" if mood_counts.get('neutral', 0) > total/2 else "😔 Vibes are off"
            
            result = f"**Server Vibes** {vibe}\n"
            for mood, count in mood_counts.items():
                emoji = {"happy": "😊", "sad": "😔", "angry": "😠", "excited": "🤩", "neutral": "😐", "confused": "🤔"}.get(mood, "😐")
                percentage = (count/total)*100
                result += f"{emoji} {mood}: {percentage:.0f}%\n"
            await ctx.send(result)
        else:
            await ctx.send("Not enough vibes to analyze yet! Get people chatting! 🎮")
    else:
        await ctx.send("No data yet! Talk to me first! 💀")

@bot.command()
async def stats(ctx):
    """Your conversation stats with me"""
    user_id = str(ctx.author.id)
    if user_id in memory:
        count = len(memory[user_id]['context'])
        await ctx.send(f"📊 {ctx.author.name}, we've had {count//2} conversations! That's {count//2} W's in my book! 🏆")
    else:
        await ctx.send(f"No history yet! Say something to me {ctx.author.name}! 🎮")

@bot.command()
async def clear(ctx):
    """Clear YOUR conversation history"""
    user_id = str(ctx.author.id)
    if user_id in memory:
        memory[user_id] = {'context': [], 'personality_traits': {}}
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
    await ctx.send(f"**📜 {SERVER_NAME} Rules:**\n1️⃣ Be cool, don't be uncool\n2️⃣ No griefing (unless it's funny)\n3️⃣ No hacking (skill issue if you do)\n4️⃣ HAVE FUN! 🎮\nBreaking rules = permanent L + ratio")

@bot.command()
async def owner(ctx):
    await ctx.send(f"👑 **Server Owner:** {OWNER}\nHe's the goat fr! Show some respect! 🐐")

@bot.command()
async def creator(ctx):
    await ctx.send(f"🤖 **My Creator:** {CREATOR_NAME}\nAbsolute legend coded me with love and caffeine! ☕")

@bot.command()
async def version(ctx):
    await ctx.send(f"📦 **{SERVER_NAME}:** {SERVER_VERSION} | 🤖 **{BOT_NAME}:** {BOT_VERSION} | **AI Engine:** Pollinations v3\nWe stay updated fr! 🔄")

@bot.command()
async def tips(ctx):
    tip = random.choice([
        "💎 Diamonds at Y=-59 in new versions, but in 1.12.2 try Y=11-12!",
        "🏠 Pro builder tip: Use stairs + slabs for DETAILS. Makes a wooden box look like a mansion!",
        "🌾 Water hydrates 4 blocks in each direction. Plan your farms!",
        "⚔️ PvP hack: W-tap to reset sprint and deal more knockback. Practice it!",
        "📚 15 bookshelves = max level 30 enchants. Math is important kids!",
        "🔥 Want ancient debris? Bed mining at Y=15 in Nether. Thank me later!",
        "🐉 The Ender Dragon? More like the Ender L-taker. You got this!",
        "🎯 Crossbows with fireworks = best crowd control. Trust me on this!",
        "🏃 Speedrunner strat: Trade with piglins for fire res before blaze fight!",
        "💀 Don't dig straight down. Unless you like surprise lava baths!"
    ])
    await ctx.send(f"{tip}\n\nWant more? Just ask me! 🔥")

@bot.command()
async def pvp(ctx):
    await ctx.send(f"🏆 **Minecraft PvP Legends:**\n• **ItzRealme** - The GOAT of {SERVER_NAME}\n• **Technoblade** - The Blood God (o7)\n• **Dream** - Manhunt legend\n• **Stimpy** - Movement god\n\nAsk me about any of them! ⚔️")

@bot.command()
async def about(ctx):
    embed = discord.Embed(title=f"🤖 About {BOT_NAME}", color=0x9b59b6)
    embed.description = f"I'm an advanced AI assistant with **sentiment analysis**, **user memory**, and **personality**!\n\nCreated by **{CREATOR_NAME}** for **{SERVER_NAME}**"
    embed.add_field(name="🧠 Features", value="• Sentiment analysis\n• User profiles\n• Mood tracking\n• Personalized responses\n• 200+ IQ (trust me)", inline=False)
    embed.add_field(name="📊 Stats", value=f"• Tracking {len(user_profiles)} users\n• {sum(len(m.get('context', [])) for m in memory.values())//2} conversations\n• 99.9% sarcasm rate", inline=False)
    embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION} | Made with 💀 and ☕")
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title=f"🎮 {BOT_NAME} - Commands Menu", color=0x3498db)
    embed.description = f"Hey {ctx.author.name}! Here's what I can do:\n\n**💬 Chat with me:** `@{BOT_NAME} your message`"
    
    embed.add_field(name="📊 Profile Commands", value="`!profile` - Your stats\n`!mood` - Your mood history\n`!vibecheck` - Server vibes\n`!stats` - Chat stats\n`!clear` - Clear history", inline=False)
    embed.add_field(name="🎮 Minecraft", value="`!ip` - Server IP\n`!tips` - Pro tips\n`!pvp` - PvP legends\n`!rules` - Server rules", inline=False)
    embed.add_field(name="🤖 Bot Info", value="`!about` - About me\n`!owner` - Server owner\n`!creator` - My creator\n`!version` - Version info\n`!ping` - Latency check\n`!help` - This menu", inline=False)
    
    embed.add_field(name="🔒 Owner Only", value="`!reset` - Reset ALL memory", inline=False)
    embed.add_field(name="✨ Features", value="• Sentiment analysis (I know how you feel)\n• Memory (I remember you)\n• Personalized responses\n• 24/7 availability", inline=False)
    embed.set_footer(text=f"Try mentioning me! @{BOT_NAME} What's up?")
    
    await ctx.send(embed=embed)

# ========== ERROR HANDLING ==========
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Bruh that command doesn't exist 💀 Try `!help` to see what I can do!")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(f"Nope {ctx.author.name}, you don't have permission for that! Nice try though 👀")
    else:
        print(f"Error: {error}")
        await ctx.send(f"Ayo {ctx.author.name}, something broke! {random.choice(['Try again?', 'My bad fr', 'Say that one more time'])} 🔄")

# ========== START BOT ==========
keep_alive()
bot.run(DISCORD_TOKEN)
