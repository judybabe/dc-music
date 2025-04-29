from discord.ext import commands
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
import asyncio
import discord
import random
import os
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# === Load environment variables ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# === Spotify API setup ===
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# === Discord bot setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

queue = []
looping = False

# === YouTube download options ===

if not os.path.exists("cookies.txt"):
    print("cookies.txt not found.")
ydl_opts = {
    'cookiefile': 'cookies.txt',
    'format': 'bestaudio',
    'quiet': True,
    'default_search': 'ytsearch',
    'noplaylist': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
    }
}

# === Bot events ===
@bot.event
async def on_ready():
    print(f"✅ 機器人已上線：{bot.user}")

# === 播放邏輯 ===
async def play_next(ctx):
    if not queue:
        return

    search = queue[0]
    vc = ctx.voice_client
    if not vc or not vc.is_connected():
        await ctx.send("❗ 我還沒加入語音頻道，請先輸入 `!join`")
        return

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            url = info['url']
            title = info.get('title', '未知歌曲')
    except Exception as e:
        print("YT-DLP 播放錯誤：", e)
        await ctx.send("⚠️ 無法播放此歌曲，可能是需要登入或請求過多。")
        queue.pop(0)
        return

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

    def after_playing(err):
        if err:
            print(f"播放中斷錯誤：{err}")
        if not looping:
            queue.pop(0)
        fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"播放後錯誤: {e}")

    vc.play(source, after=after_playing)
    await ctx.send(f"🎶 正在播放：**{title}**")

# === 指令 ===
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("你必須先加入語音頻道！")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("我不在語音頻道內。")

@bot.command()
async def play(ctx, *, search: str):
    if "open.spotify.com/track/" in search:
        track_id = search.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        song_name = track['name']
        artists = ", ".join([artist['name'] for artist in track['artists']])
        query = f"{song_name} {artists}"
        queue.append(query)
        await ctx.send(f"🎵 已加入歌曲：{query}")

    elif "open.spotify.com/playlist/" in search:
        playlist_id = search.split("/")[-1].split("?")[0]
        results = sp.playlist_tracks(playlist_id)
        for item in results['items']:
            track = item['track']
            if track:
                song_name = track['name']
                artists = ", ".join([artist['name'] for artist in track['artists']])
                query = f"{song_name} {artists}"
                queue.append(query)
        await ctx.send(f"📜 歌單已加入 {len(results['items'])} 首歌曲！")

    else:
        queue.append(search)

    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.voice_client.pause()

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        await ctx.voice_client.resume()

@bot.command()
async def loop(ctx):
    global looping
    looping = not looping
    await ctx.send(f"循環播放 {'開啟' if looping else '關閉'}")

@bot.command()
async def shuffle(ctx):
    random.shuffle(queue)
    await ctx.send("播放清單已隨機排序 🎲")

@bot.command()
async def now(ctx):
    await ctx.send(f"目前播放：{queue[0]}" if queue else "目前沒有播放歌曲。")

@bot.command()
async def stop(ctx):
    queue.clear()
    if ctx.voice_client:
        ctx.voice_client.stop()
    await ctx.send("已停止播放並清空播放清單。")

@bot.command(name="queue")
async def queue_list(ctx):
    if not queue:
        await ctx.send("播放清單是空的。")
    else:
        message = "**🎵 播放清單：**\n"
        for idx, item in enumerate(queue, start=1):
            message += f"{idx}. {item}\n"
        await ctx.send(message)

@bot.command()
async def remove(ctx, index: int):
    if 1 <= index <= len(queue):
        removed = queue.pop(index - 1)
        await ctx.send(f"🗑️ 已從播放清單移除：{removed}")
    else:
        await ctx.send("⚠️ 無效的編號，請使用 `!queue` 查看正確編號。")

@bot.command()
async def clear(ctx):
    queue.clear()
    await ctx.send("🧹 播放清單已清空（目前播放不受影響）。")


bot.run(TOKEN)
