import math
import os
import discord
from discord.ext import commands, tasks
from time import time, gmtime, strftime
from datetime import datetime, timedelta, time as dt
from dotenv import load_dotenv
import pytz
import asyncio

from rps import RPS
from weather.weather import Weather
from tides.tides import predict_tide, rebuild_model
from astro import CelestialTracker, SunArcTimer
from discord_music_core.musicbot import MusicBot

load_dotenv()
TOKEN = os.getenv('TOKEN')
SERVER = os.getenv('SERVER')

IRELAND_TZ = pytz.timezone("Europe/Dublin")
TIDE_RECIPIENTS = ['287363454665359371', '356458075302920202']
TARGET_HOUR = 13
TARGET_MINUTES = 0

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

rpsDict = {}
rpsKeys = { 'r': 0, 'rock': 0,
            'p': 1, 'paper': 1,
            's': 2, 'scissors': 2}
rpsNames = {'0': 'rock',
            '1': 'paper',
            '2': 'scissors'}
rpsOutKeys = {  '-1': 'Computer Wins!',
                '1' : 'Player Wins!',
                '0' : 'You drew!'}

def timestamp(datetime):
    return f'<t:{int(datetime.timestamp())}:t>'

def datetimestamp(datetime):
    return f'<t:{int(datetime.timestamp())}>'

def create_embed(title=None, colour=0x1E90FF, timestamp=None):
    return discord.Embed(
        title=title,
        colour=colour,  # nice blue
        timestamp=timestamp if timestamp is not None else datetime.now(pytz.utc)
    )

async def join_vc(ctx):
    if ctx.author.voice is None:
        await ctx.send("You're not connected to a voice channel.")
        return

    channel = ctx.author.voice.channel

    if ctx.voice_client is not None:
        if ctx.voice_client.channel == channel:
            return channel
        await ctx.voice_client.move_to(channel)
        await ctx.send(f"Moved to {channel.name}")
    else:
        await channel.connect()
        await ctx.send(f"Joined {channel.name}")

    return channel


def moon_info(dt=None):
    ct = CelestialTracker()
    alt, az = ct.moon_at(dt)
    _, perc = ct.moon_angular_diameter_pct(dt)
    rise, set = ct.moon_rise_set()
    rise_set_str = f'Rises @ {timestamp(rise)}' if alt <= 0 else f'Sets @ {timestamp(set)}'
    return alt, az, perc, rise_set_str

def create_ws_embed():
    w = Weather()
    s = w.sunset().astimezone(pytz.utc)
    s1 = s - timedelta(hours=1)
    s2 = s - timedelta(hours=2)
    h = predict_tide(s)[0]
    h1 = predict_tide(s1)[0]
    h2 = predict_tide(s2)[0]

    t, forecast = w.weather_at(s)
    temp = forecast["temperature"]
    temp_margin = forecast["temp_margin"]
    feels_like = forecast["feels_like"]
    weather_desc = forecast["weather"]
    wind_speed = forecast["wind_speed"]
    cloud_cover = forecast["cloud_cover"]

    alt, az, perc, rise_set_str = moon_info(s)

    embed = create_embed(title="🌅 Evening Tide, Weather & Moon Forecast")

    embed.add_field(
        name="🌊 Tide Forecast",
        value=(
            f"`{h2:.2f}` | {timestamp(s2)} m\n"
            f"`{h1:.2f}` | {timestamp(s1)} m\n"
            f"`{h:.2f}`  | {timestamp(s)} m 🌅(sunset)"
        ),
        inline=False
    )

    embed.add_field(
        name=f"🌤️ Dun Laoghaire Weather Forecast @ {timestamp(t)}",
        value=(
            f"Temperature: `{temp:.2f}±{temp_margin:.2f} °C` (feels like `{feels_like:.2f} °C`)\n"
            f"Weather: `{weather_desc}`\n"
            f"Wind Speed: `{wind_speed:.2f} m/s`\n"
            f"Cloud Cover: `{cloud_cover}%`"
        ),
        inline=False
    )

    embed.add_field(
        name=f"🌙 Moon Info @ {timestamp(s)}",
        value=(
            f"Altitude: `{alt:.1f}°`\n"
            f"Azimuth: `{az:.1f}°`\n"
            f"%size of Avg.: `{perc:.1f}%`\n"
            f"{rise_set_str}"
        ),
        inline=False
    )

    t, _ = SunArcTimer().minutes_per_hand_near_sunset()
    embed.set_footer(text=f"{t:.1f} minutes per handwidth (7.149°)")
    # embed.set_thumbnail(url="https://i.imgur.com/3ZQ3ZzL.png")  # Example weather icon

    return embed



# @asyncio.tasks.loop(hours=24)
# async def send_daily_forecast(test=False):
#     await bot.wait_until_ready()

#     while not bot.is_closed():
#         # if test is False:
#         now_utc = datetime.now(pytz.utc)
#         ireland_now = now_utc.astimezone(IRELAND_TZ)
#         target_time = IRELAND_TZ.localize(datetime.combine(ireland_now.date(), dt(hour=TARGET_HOUR)))

#         if ireland_now >= target_time:
#             target_time += timedelta(days=1)

#         wait_seconds = (target_time - ireland_now).total_seconds()

#         await asyncio.sleep(wait_seconds)

#         for id in TIDE_RECIPIENTS:
#             user = await bot.fetch_user(id)

#             # if test:
#             #     await user.send("Manual Daily Message Test")

#             try:
#                 await user.send(embed=create_ws_embed())

#             except Exception as e:
#                 print(f"Error sending forecast: {e}")
        
#         # if test: return

@tasks.loop(hours=24)
async def send_daily_forecast():
    for id in TIDE_RECIPIENTS:
        user = await bot.fetch_user(id)
        try:
            await user.send(embed=create_ws_embed())
        except Exception as e:
            print(f"Error sending forecast: {e}")

@send_daily_forecast.before_loop
async def wait_until_1pm():
    await bot.wait_until_ready()
    now = datetime.now(IRELAND_TZ)
    target_time = IRELAND_TZ.localize(datetime.combine(now.date(), dt(hour=TARGET_HOUR, minute=TARGET_MINUTES)))

    if now >= target_time:
        target_time += timedelta(days=1)

    wait_seconds = (target_time - now).total_seconds()
    # print(f"[Forecast Timer] Sleeping {wait_seconds/3600:.2f} hours until 1pm Ireland time")
    await asyncio.sleep(wait_seconds)



@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name=SERVER)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name} (id: {guild.id})'
    )

    if not send_daily_forecast.is_running():
        send_daily_forecast.start()



@bot.event
async def on_message(message):
    # skip if by bot
    if message.author == bot.user: return

    # log message
    file = 'log.csv'
    with open(file, 'a', encoding="utf-8") as f:
        f.write(f"""{strftime('%d/%m/%Y %H:%M:%S', gmtime(time()))},"{str(message.channel)}","{message.author}",{repr(message.content).replace("'",'"')}\n""")


    # react for fun
    # if str(message.author) == 'Sekai#2422':
    #   await message.add_reaction('👀')
    # if str(message.author) == 'Mango#6990':
    #   await message.add_reaction('❤️')
    # if str(message.author) == 'Bread Accountant#4781':
    #   await message.add_reaction('🤮')

    # rps game
    msg = message.content
    ID = message.author.id

    if '😎' in msg:
        await message.add_reaction('😎')

    if isinstance(message.channel, discord.DMChannel) and message.author.name == 'oneautumnmango':
        if msg.startswith('-rebuild'):
            await message.channel.send(f'Downloading new tide data and rebuilding model...')
            if rebuild_model():
                await message.channel.send(f'Success!')
            else: 
                await message.channel.send(f'Failure!')

        if msg.startswith('-wstest'):
            await send_daily_forecast(test=True)

    await bot.process_commands(message)



@bot.command(help="Play Rock-Paper-Scissors with the bot.")
async def rps(ctx, arg: str = None):
    ID = ctx.author.id

    if ID not in rpsDict:
        rps = RPS(str(ctx.author), ID, folder_path='rps logs')
        rpsDict[ID] = rps
    else:
        rps = rpsDict[ID]

    if arg is None:
        await ctx.send("Please specify your move (`rock`/`r`, `paper`/`p`, `scissors`/`s`) or `score`.")
        return

    if arg in ['score', 'stats']:
        s, w, l, d = rps.get_score()
        winrate = f"{(w / float(l + w)) * 100:.2f}%" if l + w > 0 else "N/A"
        await ctx.send(f"```Total Games Played: {w + l + d}, Winrate: {winrate}\nScore: {s}, Wins: {w}, Losses: {l}, Draws: {d}```")
        return

    if arg not in rpsKeys:
        await ctx.send(f"Input '{arg}' not recognised. Please try again.")
        return

    cin, _, pout = rps.play(rpsKeys[arg])
    await ctx.send(f'Computer played {rpsNames[str(cin)]}\n{rpsOutKeys[str(pout)]}')


@bot.command(aliases=['s'], help="Shows today's sunset time in UTC.")
async def sunset(ctx):
    await ctx.send(f'Sunset at {timestamp(Weather().sunset())}')

@bot.command(aliases=['w'], help='Gets the current weather forecast.')
async def weather(ctx):
    forecast = Weather().weather_now()
    temp = forecast["temperature"]
    temp_margin = forecast["temp_margin"]
    feels_like = forecast["feels_like"]
    weather_desc = forecast["weather"]
    wind_speed = forecast["wind_speed"]
    cloud_cover = forecast["cloud_cover"]

    embed = create_embed(f"🌤️ Weather Forecast")
    embed.add_field(
        name=f"Dun Laoghaire",
        value=(
            f"Temperature: `{temp:.2f}±{temp_margin:.2f} °C` (feels like `{feels_like:.2f} °C`)\n"
            f"Weather: `{weather_desc}`\n"
            f"Wind Speed: `{wind_speed:.2f} m/s`\n"
            f"Cloud Cover: `{cloud_cover}%`"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(aliases=['t'], help='Gets the current DL tide prediction.')
async def tide(ctx):
    now = datetime.now(pytz.utc)
    await ctx.send(f"`{predict_tide(now)[0]:.2f}m` @ {timestamp(now)}")

@bot.command(help="Gets the altitude and azimuth (angle off north) of the Moon.")
async def moon(ctx):
    alt, az, perc, rise_set_str = moon_info()
    # await ctx.send(f"Moon Alt: `{alt:.1f}°`, Az: `{az:.1f}°`, `{perc:.1f}%` of avg., {rise_set_str}")
    embed = create_embed(f"🌙 Moon Info")
    embed.add_field(
        name=f"Details",
        value=(
            f"Altitude: `{alt:.1f}°`\n"
            f"Azimuth: `{az:.1f}°`\n"
            f"%size of Avg.: `{perc:.1f}%`\n"
            f"{rise_set_str}"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(help="Gets the altitude and azimuth (angle off north) of the Sun.")
async def sun(ctx):
    alt, az = CelestialTracker().sun_at()
    await ctx.send(f"Sun Alt: `{alt:.1f}°`, Az: `{az:.1f}°`")


@bot.command(help="Tide and weather around today's sunset.")
async def ws(ctx):
    await ctx.send(embed=create_ws_embed())

@bot.command(aliases=['hori', 'h'], help="Calculates the distance to the horizon from a given height.")
async def horizon(ctx, height: float):
    if height < 0:
        await ctx.send("Height must be non-negative.")
        return

    r = 6356752.3
    # distance_m = math.sqrt((r+height)**2 - r**2)
    distance_m = math.sqrt(2*r*height + height **2)
    distance_km = distance_m/1000

    await ctx.send(
        f"At a height of `{height:.2f}m`, the horizon is approximately `{distance_km:.2f}km` away."
    )

@bot.command(help="Time in minutes for the sun to travel one handwidth. (avg of last 2 handwidths)")
async def handtime(ctx):
    t, _ = SunArcTimer().minutes_per_hand_near_sunset()
    await ctx.send(f"`{t:.1f}` minutes per handwidth (`7.149°`)")

# ============ Music =============
@bot.command(help="Joins Music Channel")
async def join(ctx):
    await join_vc(ctx)

@bot.command(help="Leaves the current voice channel")
async def leave(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not in a voice channel.")
        return

    await ctx.voice_client.disconnect()
    await ctx.send("Disconnected from the voice channel.")

@bot.command(help="Play a song from a YouTube URL")
async def play(ctx, *, url: str):
    await join_vc(ctx)

    # Pass the current voice client to MusicBot if you haven't already
    if not hasattr(ctx.bot, "musicbot"):
        loop = asyncio.get_running_loop()
        ctx.bot.musicbot = MusicBot(ctx.voice_client, loop)
    else:
        # Update voice client if changed
        if ctx.bot.musicbot.voice_client != ctx.voice_client:
            ctx.bot.musicbot.voice_client = ctx.voice_client

    # Use your MusicBot instance to queue the song
    await ctx.bot.musicbot.play(url)

    # await ctx.send(f"Added to queue: {url}")

@bot.command(help="Skips current song.")
async def skip(ctx):
    if not hasattr(bot, "musicbot"):
        await ctx.send("Music bot is not initialized.")
        return

    bot.musicbot.skip()
    await ctx.send("Skipped the current song.")

@bot.command(aliases=["now"], help="Shows the current song playing.")
async def nowplaying(ctx):
    if not hasattr(bot, "musicbot"):
        await ctx.send("Music bot is not initialized.")
        return

    current = bot.musicbot.get_current()
    if current:
        await ctx.send(f"Currently playing: {current}")
    else:
        await ctx.send("No song is currently playing.")

@bot.command(aliases=["list"], help="Shows the titles in the queue.")
async def queue(ctx):
    if not hasattr(bot, "musicbot"):
        await ctx.send("Music bot is not initialized.")
        return

    queue_items = bot.musicbot.get_queue()
    if not queue_items:
        await ctx.send("The queue is empty.")
        return

    # queue_items are tuples (url, title), so just get titles:
    titles = [title for url, title in queue_items]

    await ctx.send("Queue:\n" + "\n".join(f"- `{title}`" for title in titles))

@bot.command(help="Stops music playback and clears the queue.")
async def stop(ctx):
    if hasattr(bot, "musicbot"):
        bot.musicbot.stop()
    else:
        await ctx.send("Music bot is not initialized.")

@bot.command(help="Pauses music.")
async def pause(ctx):
    if hasattr(bot, "musicbot"):
        bot.musicbot.pause()
        await ctx.send("Playback paused.")
    else:
        await ctx.send("Music bot is not initialized.")

@bot.command(help="Resumes music.")
async def resume(ctx):
    if hasattr(bot, "musicbot"):
        bot.musicbot.resume()
        await ctx.send("Playback resumed.")
    else:
        await ctx.send("Music bot is not initialized.")


# ================================

bot.run(TOKEN)
 
