import json
from classes import Team, Map
from typing import Iterable
import aiohttp
from valve.rcon import RCON

async def generate_config(team1: Team, team2: Team, maps: Iterable[Map]):
    config = {}
    # Match settings
    config["matchid"] = f"{team1.name} vs {team2.name}"
    config["num_maps"] = len(maps)
    config["maplist"] = [m.ingame_name for m in maps]
    config["skip_veto"] = True
    config["map_sides"] = []
    for m in maps:
        if m.sides["ct"] == team1:
            config["map_sides"].append("team1_ct")
        elif m.sides["ct"] == team2:
            config["map_sides"].append("team2_ct")
        else:
            config["map_sides"].append("knife")
    # Team settings
    for i, team in enumerate([team1, team2]):
        config[f"team{i+1}"] = {}
        t = config[f"team{i+1}"]
        t["name"] = team.name
        t["players"] = [str(i) for i in await team.get_players_steam_ids()]
    
    with open("get5/configs/match_config.json", 'w') as f:
        json.dump(config, f)

    return config

def get_config_from_file():
    with open("configs/match_config.json") as f:
        config = json.load(f)
    return config

def send_rcon_loadmatch():
    rcon('get5_loadmatch_url "http://theobrown.uk/match_config"')

def rcon(command='status', server_ip="194.147.121.4", server_port=27083, password="61g75"):
    with RCON((server_ip, server_port), password) as rcon_connection:
        response = rcon_connection(command)
    return response
