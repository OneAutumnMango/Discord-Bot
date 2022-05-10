import random
import os
import json


def randomRPS():
    return random.randint(0, 2)


class RPS():  # r p s = 0 1 2
    
    def __init__(self, player_name, ID, AI=randomRPS, folder_path='.'):
        self.player_name = player_name  # used to separate data between players
        self.ID = ID  
        self.AI = AI                    # func to generate computer choice
        self.folder_path = folder_path  # folder to store data
        
        self.generate_file()
    
    def play(self, player_in):
        comp_in = self.AI()
        outcome = self.get_outcome(comp_in, player_in)
        
        self.add_game(comp_in, player_in, outcome)
        return comp_in, player_in, outcome
 
    
    def get_outcome(self, comp_in: int, player_in: int) -> int:  # input is one of [0, 1, 2]
        if comp_in == player_in:
            return 0  # tie
        elif comp_in == (player_in + 1) % 3:
            return -1  # player loses
        return 1     # player wins


    def generate_file(self, reset=False):
        self.path = f'{self.folder_path}/{self.player_name}.json'
        if os.path.exists(self.path) and not reset:
            print(f'File {self.path} already exists. Reading data...')
            with open(self.path, 'r') as f:
                self.file = json.load(f)
            return
        
        self.file = {
    'ID': self.ID,
    'Name': self.player_name,
    'rps': {
        'score': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'data': [
            ["Cin", "Pin", "Pout"] # comp_in, player_in, player_out  (comp_out = -player_out)
        ]
    }
}

        with open(self.path, 'w') as f:
            json.dump(self.file, f, indent=4)


    def add_game(self, comp_in, player_in, outcome):
        rps = self.file['rps']

        if outcome == -1: rps['losses'] += 1
        elif outcome == 1: rps['wins'] += 1
        else: rps['draws'] += 1

        rps['data'].append([comp_in, player_in, outcome])
        rps['score'] += outcome

        with open(self.path, 'w') as f:
            json.dump(self.file, f, indent=4)


    def get_score(self):
        rps = self.file['rps']
        return rps['score'], rps['wins'], rps['losses'], rps['draws']
