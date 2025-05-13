import os
import discord
from time import time, gmtime, strftime
from datetime import datetime, timedelta, time as dt
from dotenv import load_dotenv
import pytz
import asyncio

from rps import RPS
from weather.weather import Weather
from tides.tides import predict_tide, rebuild_model

load_dotenv()
TOKEN = os.getenv('TOKEN')
SERVER = os.getenv('SERVER')

IRELAND_TZ = pytz.timezone("Europe/Dublin")
TIDE_RECIPIENTS = ['287363454665359371']
TARGET_HOUR = 13

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

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



# @asyncio.tasks.loop(hours=24)
async def send_daily_forecast():
    await client.wait_until_ready()

    while not client.is_closed():
        now_utc = datetime.now(pytz.utc)
        ireland_now = now_utc.astimezone(IRELAND_TZ)
        target_time = IRELAND_TZ.localize(datetime.combine(ireland_now.date(), dt(hour=TARGET_HOUR)))

        if ireland_now >= target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - ireland_now).total_seconds()

        await asyncio.sleep(wait_seconds)

        for ids in TIDE_RECIPIENTS:
            user = await client.fetch_user(ids)

            try:
                w = Weather()

                s = w.sunset().astimezone(pytz.utc)
                s1 = s - timedelta(hours=1)
                s2 = s - timedelta(hours=2)
                h = predict_tide(s)[0]
                h1 = predict_tide(s1)[0]
                h2 = predict_tide(s2)[0]

                tide_msg = (
                    "**Daily Tide Forecast:**\n"
                    f"`{h2:.2f}m` @ {timestamp(s2)}\n"
                    f"`{h1:.2f}m` @ {timestamp(s1)}\n"
                    f"`{h:.2f}m` @ {timestamp(s)} (sunset)"
                )

                t, forecast = w.weather_at(s)
                weather_msg = f"**Weather Forecast:** @ {timestamp(t)}\n" + forecast

                await user.send(tide_msg)
                await user.send(weather_msg)

            except Exception as e:
                print(f"Error sending forecast: {e}")



@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=SERVER)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name} (id: {guild.id})'
    )
    asyncio.create_task(send_daily_forecast())



@client.event
async def on_message(message):
    # skip if by bot
    if message.author == client.user: return

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



    if msg.startswith('-rps'):
        try:
            arg = msg.split("-rps ", 1)[1]  # splits once on '-rps ' and takes whats after (the input)
        except IndexError:
            return


        # create class instance/get reference to existing
        if ID not in rpsDict: 
            rps = RPS(str(message.author), ID, folder_path='rps logs')
            rpsDict[ID] = rps
        else:
            rps = rpsDict[ID]


        if arg in ['score', 'stats']:
            s, w, l, d = rps.get_score()
            winrate = f"{(w/float(l+w))*100:.2f}%" if l + w > 0 else "N/A"
            await message.channel.send(f"```Total Games Played: {w+l+d}, Winrate: {winrate}\nScore: {s}, Wins: {w}, Losses: {l}, Draws: {d}```")
            return


        # check for valid input
        if arg not in rpsKeys:
            await message.channel.send(f"Input '{arg}' not recognised. Please try again.")
            return



        # play
        cin, _, pout = rps.play(rpsKeys[arg])
        await message.channel.send(f'Computer played {rpsNames[str(cin)]}\n{rpsOutKeys[str(pout)]}')

    
    if isinstance(message.channel, discord.DMChannel) and message.author.name == 'oneautumnmango':
        if msg.startswith('-rebuild'):
            await message.channel.send(f'Downloading new tide data and rebuilding model...')
            if rebuild_model():
                await message.channel.send(f'Success!')
            else: 
                await message.channel.send(f'Failure!')

    if msg.startswith('-sunset'):
        await message.channel.send(f'Sunset at {timestamp(Weather().sunset())}')

    elif msg.startswith('-tide'):
        now = datetime.now(pytz.utc)
        await message.channel.send(f"`{predict_tide(now)[0]:.2f}m` @ {timestamp(now)}")
        
    elif msg.startswith('-weather'):
        await message.channel.send("**Weather Forecast:**\n" + Weather().weather_now())

    elif msg.startswith('-ws'):
        w = Weather()
        s = w.sunset().astimezone(pytz.utc)
        s1 = s - timedelta(hours=1)
        s2 = s - timedelta(hours=2)
        h = predict_tide(s)[0]
        h1 = predict_tide(s1)[0]
        h2 = predict_tide(s2)[0]

        tide_msg = (
            "**DL Tide Forecast:**\n"
            f"`{h2:.2f}m` @ {timestamp(s2)}\n"
            f"`{h1:.2f}m` @ {timestamp(s1)}\n"
            f"`{h:.2f}m` @ {timestamp(s)} (sunset)"
        )

        t, forecast = w.weather_at(s)

        weather_msg = f"**Weather Forecast:** @ {timestamp(t)}\n" + forecast

        await message.channel.send(tide_msg)
        await message.channel.send(weather_msg)


client.run(TOKEN)
 
