import discord
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread
import google.generativeai as genai
from pytube import YouTube
from pytube.exceptions import PytubeError

# Flask server setup
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Configure Gemini API
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# Function to get Gemini response
async def get_gemini_response(prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text

# Enable necessary Discord intents
intents = discord.Intents.default()
intents.message_content = True  # REQUIRED to read message content
intents.guilds = True
intents.members = True

# Set up bot with intents
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # Disable the default help command

# Queue for storing songs
song_queue = []

# Global loop flag
loop_enabled = False

# Function to extract video URLs from a YouTube playlist
def extract_playlist_urls(playlist_url):
    try:
        yt = YouTube(playlist_url)
        return [playlist_url]  # pytube doesn't support playlists directly, so treat as single video
    except PytubeError:
        return []

# Function to search YouTube for a video URL
def search_youtube(query):
    try:
        yt = YouTube(query)
        return yt.watch_url
    except PytubeError:
        return None

# Function to play the next song in the queue
async def play_next(ctx):
    global song_queue, loop_enabled

    if song_queue:
        url = song_queue.pop(0)
        await play_url(ctx, url)

        # If looping is enabled, re-add the song to the end of the queue
        if loop_enabled:
            song_queue.append(url)

# Function to play an individual URL
async def play_url(ctx, url):
    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    try:
        # Use pytube to extract the audio stream URL
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            await ctx.send("❌ Could not extract audio stream.")
            return

        # Download the audio stream
        audio_file = audio_stream.download(filename="audio.mp3")

        # Play the audio using FFmpeg
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        audio_source = discord.FFmpegPCMAudio(audio_file, **ffmpeg_options)

        if not voice_client.is_playing():
            voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send(f"🎶 Now playing: {yt.title}")

        # Clean up the downloaded file
        os.remove(audio_file)
    except PytubeError as e:
        await ctx.send(f"❌ Error: {str(e)}")

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

# Command to pause the current song
@bot.command()
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.send("⏸️ Music paused.")

# Command to resume the paused song
@bot.command()
async def resume(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("▶️ Music resumed.")

# Command to stop music and clear the queue
@bot.command()
async def stop(ctx):
    global song_queue, loop_enabled
    song_queue.clear()
    loop_enabled = False  # Disable looping when stopping
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("⏹️ Music stopped, queue cleared, and loop disabled.")

# Command to toggle looping
@bot.command()
async def loop(ctx):
    global loop_enabled
    loop_enabled = not loop_enabled  # Toggle the loop flag
    status = "enabled" if loop_enabled else "disabled"
    await ctx.send(f"🔁 Loop is now **{status}**.")

# Command to chat with Gemini
@bot.command()
async def chat(ctx, *, message: str):
    await ctx.send("🤖 Thinking...")
    response = await get_gemini_response(message)
    await ctx.send(f"💬 {response}")

# Custom help command
@bot.command()
async def help(ctx):
    help_message = """
🎶 **Music Bot Commands** 🎶

**!play <query or URL>** - Play a song or add it to the queue. You can use a YouTube URL or search for a song by name.
**!skip** - Skip the currently playing song.
**!pause** - Pause the currently playing song.
**!resume** - Resume the paused song.
**!stop** - Stop the music, clear the queue, and disconnect the bot.
**!loop** - Toggle looping for the current song.
**!chat <message>** - Chat with the Gemini AI.
**!help** - Show this help message.

🔗 **Examples**:
- `!play Never Gonna Give You Up`
- `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- `!skip`
- `!loop`
- `!chat What's the weather like today?`
"""
    await ctx.send(help_message)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# Run bot using an environment variable
keep_alive()
TOKEN = os.getenv("DISCORD_TOKEN")  # Set your token in Replit's Secrets
bot.run(TOKEN)
