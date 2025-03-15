# Function to search YouTube for a video URL
def search_youtube(query):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'format': 'bestaudio/best',
        'cookiefile': 'cookies.txt',  # Add this line
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
        'cookiefile': 'cookies.txt',  # Add this line
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
