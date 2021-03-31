import json
from classes import Team, Map, Match
from typing import Iterable
import aiorcon
import asyncio
from os import getenv

async def generate_config(match: Match):
    config = {}
    # Match settings
    config["matchid"] = f"{match.teams[0].name} vs {match.teams[1].name}"
    config["num_maps"] = len(match.maps)
    config["maplist"] = [m.ingame_name for m in match.maps]
    config["skip_veto"] = True
    config["cvars"] = {}
    if '2v2' in match.gametype:
        config["cvars"]["get5_warmup_cfg"] = "get5/warmup_2v2.cfg"
        config["cvars"]["get5_live_cfg"] = "get5/live_2v2.cfg"
        config["players_per_team"] = 2
    else:
        config["cvars"]["get5_warmup_cfg"] = "get5/warmup_5v5.cfg"
        config["cvars"]["get5_live_cfg"] = "get5/live_5v5.cfg"
        config["players_per_team"] = 5
    config["map_sides"] = []
    for m in match.maps:
        if m.sides["ct"] == match.teams[0]:
            config["map_sides"].append("team1_ct")
        elif m.sides["ct"] == match.teams[1]:
            config["map_sides"].append("team2_ct")
        elif m.sides["t"] == match.teams[0]:
            config["map_sides"].append("team1_t")
        elif m.sides["t"] == match.teams[1]:
            config["map_sides"].append("team2_t")
        else:
            config["map_sides"].append("knife")
    # Team settings
    for i, team in enumerate(match.teams):
        config[f"team{i+1}"] = {}
        t = config[f"team{i+1}"]
        t["name"] = team.name
        t["tag"] = ""
        steam_ids = await team.get_players_steam_ids()
        t["players"] = {str(steam_id): str(user.nick) for steam_id, user in zip(steam_ids, team.players)}
    
    with open("get5/configs/match_config.json", 'w') as f:
        json.dump(config, f)

    return config

def get_config_from_file():
    with open("configs/match_config.json") as f:
        config = json.load(f)
    return config

async def loadmatch(ip, port, rcon_password):
    await rcon(ip, port, rcon_password, f"get5_loadmatch_url \"{getenv('MATCH_CONFIG_URL')}\"")

async def endmatch(ip, port, rcon_password):
    await rcon(ip, port, rcon_password, f"get5_endmatch")

async def force_loadmatch(ip, port, rcon_password):
    await rcon(ip, port, rcon_password, f"get5_endmatch; get5_loadmatch_url \"{getenv('MATCH_CONFIG_URL')}\"")

async def rcon(ip, port, rcon_password, command):
    rconsole = await aiorcon.RCON.create(ip, int(port), rcon_password, loop=asyncio.get_event_loop())
    response = await rconsole(command)
    rconsole.close()
    return response

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv('../.env')