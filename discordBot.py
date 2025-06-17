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
from celestialtracker import CelestialTracker, SunArcTimer

load_dotenv()
TOKEN = os.getenv('TOKEN')
SERVER = os.getenv('SERVER')

IRELAND_TZ = pytz.timezone("Europe/Dublin")
TIDE_RECIPIENTS = ['287363454665359371', '356458075302920202']
TARGET_HOUR = 13
TARGET_MINUTES = 0
COMMAND_PREFIX='/'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

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
    phase, illum = ct.moon_phase(dt)
    phase_name = ct.moon_phase_name(phase)
    return alt, az, perc, rise_set_str, phase, phase_name, illum

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

    alt, az, perc, rise_set_str, phase, phase_name, illum = moon_info(s)

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
        name=f"🌙 Moon Info @ {timestamp(s)} (sunset)",
        value=(
            f"Altitude: `{alt:.1f}°`\n"
            f"Azimuth: `{az:.1f}°`\n"
            f"%size of Avg.: `{perc:.1f}%`\n"
            f"{rise_set_str}\n"
            f"Phase: {phase_name} (`{phase:.1f}°`)\n"
            f"Illumination `{illum*100:.1f}%`"
        ),
        inline=False
    )

    if s > datetime.now(pytz.utc) + timedelta(hours=2):
        t, _ = SunArcTimer().minutes_per_hand_near_sunset()
        embed.set_footer(text=f"{t:.1f} minutes per handwidth (7.149°)")
    # embed.set_thumbnail(url="https://i.imgur.com/3ZQ3ZzL.png")  # Example weather icon

    return embed



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

    activity = discord.Game(name=f"music 🎵 | {COMMAND_PREFIX}help")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    # await bot.tree.sync(guild=discord.Object(id=guild.id))
    await bot.tree.sync()

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


    msg = message.content
    ID = message.author.id

    if '😎' in msg:
        await message.add_reaction('😎')

    if message.author.name == 'oneautumnmango':
        if msg.startswith('-rebuild'):
            await message.channel.send(f'Downloading new tide data and rebuilding model...')
            if rebuild_model():
                await message.channel.send(f'Success!')
            else: 
                await message.channel.send(f'Failure!')

        if msg.startswith('-wstest'):
            await send_daily_forecast(test=True)

        if msg.startswith('-musicinfo'):
            await message.channel.send(f'{bot.musicbot.last_played=}')

    await bot.process_commands(message)



@bot.tree.command(name="rps", description="Play Rock-Paper-Scissors or view your score.")
@discord.app_commands.describe(
    move="Your move: rock (r), paper (p), scissors (s), or 'score' to view stats."
)
async def rps(interaction: discord.Interaction, move: str):
    ID = interaction.user.id

    if ID not in rpsDict:
        rps = RPS(str(interaction.user), ID, folder_path='rps logs')
        rpsDict[ID] = rps
    else:
        rps = rpsDict[ID]

    move = move.lower()
    if move in ['score', 'stats']:
        s, w, l, d = rps.get_score()
        winrate = f"{(w / float(l + w)) * 100:.2f}%" if l + w > 0 else "N/A"
        await interaction.response.send_message(
            f"```Total Games Played: {w + l + d}, Winrate: {winrate}\n"
            f"Score: {s}, Wins: {w}, Losses: {l}, Draws: {d}```"
        )
        return

    if move not in rpsKeys:
        await interaction.response.send_message(
            f"Input '{move}' not recognised. Try rock (r), paper (p), scissors (s), or score.",
            ephemeral=True
        )
        return

    cin, _, pout = rps.play(rpsKeys[move])
    await interaction.response.send_message(
        f'Computer played **{rpsNames[str(cin)]}**\n{rpsOutKeys[str(pout)]}'
    )

@bot.tree.command(name="help", description="List all available commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Available Commands", color=discord.Color.blurple())

    for cmd in bot.tree.get_commands():
        embed.add_field(name=f"{COMMAND_PREFIX}{cmd.name}", value=cmd.description or "No description", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)



async def main():
    await bot.load_extension('cogs.music')
    await bot.load_extension('cogs.astro')

    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

 
