import os
import discord
from time import time, gmtime, strftime
from dotenv import load_dotenv

from rps import RPS

load_dotenv()
TOKEN = os.getenv('TOKEN')
SERVER = os.getenv('SERVER')
client = discord.Client()
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


@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=SERVER)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name} (id: {guild.id})'
    )



@client.event
async def on_message(message):
    # skip if by bot
    if str(message.author) == 'MangoPi#8181': return


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
            await message.channel.send(f"```Total Games Played: {w+l+d}, Winrate: {w/float(l+w):.2f}\nScore: {s}, Wins: {w}, Losses: {l}, Draws: {d}```")
            return


        # check for valid input
        if arg not in rpsKeys:
            await message.channel.send(f"Input '{arg}' not recognised. Please try again.")
            return



        # play
        cin, _, pout = rps.play(rpsKeys[arg])
        await message.channel.send(f'Computer played {rpsNames[str(cin)]}\n{rpsOutKeys[str(pout)]}')



    

client.run(TOKEN)
 