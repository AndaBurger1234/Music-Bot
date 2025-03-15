import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# Enable necessary Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Set up bot with intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Queue for storing songs
song_queue = []

# Function to extract video URLs from a YouTube playlist
def extract_playlist_urls(playlist_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Don't download, just get URLs
        'force_generic_extractor': True,
        'cookiefile': 'cookies.txt',  # Use cookies for authentication
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if "entries" in info:
            return [entry["url"] for entry in info["entries"] if entry.get("url")]
    return []

# Function to search YouTube for a video URL
def search_youtube(query):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'format': 'bestaudio/best',
        'cookiefile': 'cookies.txt',  # Use cookies for authentication
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info and len(info["entries"]) > 0:
            # Extract the URL of the first search result
            first_entry = info["entries"][0]
            if "url" in first_entry:
                return first_entry["url"]
            elif "webpage_url" in first_entry:
                return first_entry["webpage_url"]
    return None

# Function to play the next song in the queue
async def play_next(ctx):
    if song_queue:
        url = song_queue.pop(0)
        await play_url(ctx, url)

# Function to play an individual URL
async def play_url(ctx, url):
    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    # Use yt-dlp to extract the direct audio stream URL
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': False,
        'cookiefile': 'cookies.txt',  # Use cookies for authentication
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'url' in info:
            audio_url = info['url']
        else:
            await ctx.send("❌ Could not extract audio URL.")
            return

    # Play the audio using FFmpeg
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }
    audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)

    if not voice_client.is_playing():
        voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"🎶 Now playing: {info.get('title', 'Unknown Title')}")

# Command to play a song or playlist
@bot.command()
async def play(ctx, *, query: str):
    global song_queue

    if "playlist" in query:  # Check if it's a playlist URL
        urls = extract_playlist_urls(query)
        if urls:
            song_queue.extend(urls)  # Add all songs to queue
            await ctx.send(f"📜 Added **{len(urls)}** songs from the playlist to the queue!")
        else:
            await ctx.send("⚠️ Couldn't retrieve playlist. Please check the URL.")
    elif "youtube.com" in query or "youtu.be" in query:  # If direct YouTube link
        song_queue.append(query)
    else:  # If it's a search term
        video_url = search_youtube(query)
        if video_url:
            song_queue.append(video_url)
            await ctx.send(f"🔍 Found and added: {query}")
        else:
            await ctx.send("❌ No results found on YouTube.")

    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await play_next(ctx)  # Start playing if nothing is playing

# Command to skip the current song
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped to the next song!")
        await play_next(ctx)

# Command to stop music and clear the queue
@bot.command()
async def stop(ctx):
    global song_queue
    song_queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("⏹️ Music stopped and queue cleared.")

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# Run bot using an environment variable
TOKEN = os.getenv("DISCORD_TOKEN")  # Set your token in Replit's Secrets
bot.run(TOKEN)
