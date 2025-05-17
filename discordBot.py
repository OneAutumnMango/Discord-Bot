import math
import os
import discord
from discord.ext import commands
from time import time, gmtime, strftime
from datetime import datetime, timedelta, time as dt
from dotenv import load_dotenv
import pytz
import asyncio

from rps import RPS
from weather.weather import Weather
from tides.tides import predict_tide, rebuild_model
from astro import CelestialTracker

load_dotenv()
TOKEN = os.getenv('TOKEN')
SERVER = os.getenv('SERVER')

IRELAND_TZ = pytz.timezone("Europe/Dublin")
TIDE_RECIPIENTS = ['287363454665359371', '356458075302920202']
TARGET_HOUR = 13

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
            f"`{h:.2f}`  | {timestamp(s)}  m 🌅(sunset)"
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

    # embed.set_footer(text="Data provided by OpenWeatherAPI & Tide Prediction Algorithms")
    # embed.set_thumbnail(url="https://i.imgur.com/3ZQ3ZzL.png")  # Example weather icon

    return embed



# @asyncio.tasks.loop(hours=24)
async def send_daily_forecast(test=None):
    await bot.wait_until_ready()

    while not bot.is_closed():
        if not test:
            now_utc = datetime.now(pytz.utc)
            ireland_now = now_utc.astimezone(IRELAND_TZ)
            target_time = IRELAND_TZ.localize(datetime.combine(ireland_now.date(), dt(hour=TARGET_HOUR)))

            if ireland_now >= target_time:
                target_time += timedelta(days=1)

            wait_seconds = (target_time - ireland_now).total_seconds()

            await asyncio.sleep(wait_seconds)

        for ids in TIDE_RECIPIENTS:
            user = await bot.fetch_user(ids)

            if test:
                await user.send("Manual Daily Message Test")

            try:
                await user.send(embed=create_ws_embed())

            except Exception as e:
                print(f"Error sending forecast: {e}")
        
        if test: return



@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, name=SERVER)
    print(
        f'{bot.user} is connected to the following guild:\n'
        f'{guild.name} (id: {guild.id})'
    )
    asyncio.create_task(send_daily_forecast())



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


bot.run(TOKEN)
 
