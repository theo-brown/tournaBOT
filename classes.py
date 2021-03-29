from discord import Member, Role
import database.users
from bidict import bidict

class Team:
    def __init__(self, team, captain=None, players=[]):
        if isinstance(team, Role):
            self.players = set(team.members)
            self.name = team.name
            self.mention = team.mention
            self.ping = team.mention
            if isinstance(captain, Member) and captain in self.players:
                self.captain = captain
            else:
                self.captain = None
        elif isinstance(team, Member):
            self.captain = team
            self.players = set(players + [self.captain])
            self.name = f"team_{self.captain.name}"
            self.mention = self.name
            self.ping = self.captain.mention
        else:
            raise ValueError(f"Expected a Role and/or a Member "
                             f"(got {type(team)} and {type(captain)})")

    def add_player(self, player):
        self.players.add(player)
    
    def display(self):
        s = ""
        for player in self.players:
            s += f"{player.mention}\n"
        return s
    
    def get_players_ids(self):
        return [player.id for player in self.players]
    
    async def get_players_steam_ids(self):
        steam_ids = await database.users.get_steam64_ids(self.get_players_ids())
        if isinstance(steam_ids, int):
            return [steam_ids]
        else:
            return steam_ids


wingman_maps_by_name = bidict({'Cobblestone': 'de_cbble',
                              'Inferno': 'de_inferno',
                              'Nuke': 'de_shortnuke',
                              'Overpass': 'de_overpass',
                              'Shortdust': 'de_shortdust',
                              'Train': 'de_train',
                              'Vertigo': 'de_vertigo'})

active_duty_maps_by_name = bidict({'Dust 2': 'de_dust2',
                                  'Inferno': 'de_inferno',
                                  'Mirage': 'de_mirage',
                                  'Nuke': 'de_nuke',
                                  'Overpass': 'de_overpass',
                                  'Train': 'de_train',
                                  'Vertigo': 'de_vertigo'})


class Map:
    def __init__(self, ingame_name):
        self.ingame_name = ingame_name
        self.sides = {"t": None, "ct": None}
        self.pickedby = None
        self.knife = False
        
    def pick(self, team: Team):
        self.pickedby = team

    def choose_knife(self):
        self.knife = True

    def choose_side(self, team: Team, side: str):
        side = side.lower()
        if side in self.sides.keys():
            self.sides[side] = team
        else:
            raise KeyError(f"side must be one of {list(self.sides.keys())} (got {side})")

class Match:
    def __init__(self, team1: Team, team2: Team, gametype='5v5', bestof=3):
        self.teams = [team1, team2]
        self.maps = []
        if gametype in ['5v5', '2v2']:
            self.gametype = gametype
        else:
            raise ValueError(f"gametype must be one of ['5v5', '2v2'] (got {gametype})")
        if bestof in [1, 3]:
            self.bestof = bestof
        else:
            raise ValueError(f"bestof must be one of [1, 3] (got {bestof})")

    def pick(self, map_: Map, team: Team):
        if team in self.teams:
            map_.pick(team)
            self.maps.append(map_)
        elif team is None:
            map_.choose_knife()
            self.maps.append(map_)
        else:
            raise ValueError(f"team must be in {self.teams} or None (got {team})")

    def choose_side(self, map_: Map, team: Team, side: str):
        if map_ not in self.maps:
            raise ValueError(f"map_ must be in {self.maps} (got {map_})")
        if team not in self.teams:
            raise ValueError(f"team must be in {[t.name for t in self.teams]} (got {team.name})")
        other_side = 'ct' if side == 't' else 't'
        other_team = self.teams[0] if team == self.teams[1] else self.teams[1]
        for m in self.maps:
            if m == map_:
                map_.choose_side(team, side)
                map_.choose_side(other_team, other_side)