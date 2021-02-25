import discord
from discord import Role, Embed, Colour, Member, AllowedMentions, utils
from discord.ext import commands
from typing import Union
from sql import channels as chn
from sql import leaderboards as ldb
import parsing, menus
from classes import Map, Team

# Enable the bot to see members roles etc
bot_intents = discord.Intents.default()
bot_intents.members = True

# Create a bot instance
bot = commands.Bot(command_prefix='!', intents=bot_intents)

# Create the sql tables if they don't exist
chn.create()
ldb.create()

###############################################################################
###############################################################################

# EVENTS

@bot.event
async def on_ready():
    print("Connected as {}".format(bot.user))

@bot.listen()
async def on_message(message):
    await bot.process_commands(message)
    if chn.get_autodelete(message.channel.id) and not message.author.bot:
        await message.delete(delay=10)

###############################################################################
###############################################################################

# MODERATOR COMMANDS

@bot.command()
@commands.has_permissions(manage_channels=True)
async def channels2(ctx, mode="show", mode_arg=''):
    mentioned_channels = ctx.message.raw_channel_mentions
    help_str = "Usage: `!channels [show/add/del/help] [autodelete <#channel(s)>] [redirect <#channel1> <#channel2>]`"
    if mode == "show":
        await ctx.send(chn.display(mode_arg))
    elif mode == "add":
        if mode_arg == "redirect":
            chn.set_redirectchannel(*mentioned_channels)
            await ctx.send("Redirecting bot responses from <#{}> to <#{}>".format(*mentioned_channels),
                     delete_after=10)
        elif mode_arg == "autodelete":
            for channel in mentioned_channels:
                chn.set_autodelete(channel, True)
                await ctx.send("Autodeleting bot triggers in <#{}>".format(channel))
        else:
            await ctx.send(help_str, delete_after=10)
    elif mode == "del":
        if mode_arg == "redirect":
            for channel in mentioned_channels:
                chn.set_redirectchannel(channel, channel)
                await ctx.send("Removed redirecting bot responses from <#{}>".format(channel),
                               delete_after=10)
        elif mode_arg == "autodelete":
            for channel in mentioned_channels:
                chn.set_autodelete(channel, False)
                await ctx.send("Removed autodeleting bot triggers in <#{}>".format(channel),
                         delete_after=10)
        else:
            if mentioned_channels:
                for channel in mentioned_channels:
                    chn.delete_row(channel)
                    await ctx.send("Removing entry <#{}>".format(channel))
            else:
                await ctx.send(help_str, delete_after=10)
    elif mode == "help":
        await ctx.send(help_str, delete_after=10)


###############################################################################
###############################################################################

# MATCH COMMAND

@bot.command()
async def match2(ctx, team1: Union[Role, Member], team2: Union[Role, Member], 
                 *schedule_args):
    schedule_args = " ".join(schedule_args)
    # Parse schedule string
    datetime_obj, datetime_str = parsing.parse_date(schedule_args)
    embed = Embed(title="**Match scheduled**", colour=Colour.gold())
    embed.set_footer(text=datetime_str)

    for i, team in enumerate((team1, team2)):
        emoji = f'{i+1}\N{COMBINING ENCLOSING KEYCAP} '
        if isinstance(team, Member):
            embed.add_field(name=emoji, value=team.mention)
        elif isinstance(team, Role):
            embed.add_field(name=emoji+team.name, 
                            value='\n'.join(m.mention for m in team.members))
        else:
            await ctx.send(f"Error: teams must be mentioned by role or user "
                           f"({team} is {type(team)}")
            return

    send_channel = ctx.guild.get_channel(chn.get_redirect_channel(ctx.channel.id))
    match_message = await send_channel.send(embed=embed)
    await match_message.add_reaction("1\N{COMBINING ENCLOSING KEYCAP}")
    await match_message.add_reaction("2\N{COMBINING ENCLOSING KEYCAP}")

###############################################################################

# RESULT COMMAND
@bot.command()
async def result2(ctx, *args):
    args = list(args) # we need args to be mutable to be able to remove the team names
    if len(args) == 0:
        await ctx.send("Error: `!result` expects arguments: either scores only "
                       "(e.g. `16-10 15-16 etc`), or maps/games and scores "
                       "e.g. `Map1 16-10 etc`)")
        return
    match_message = None
    teams, players = ['', ''], ['', '']
    if ctx.message.reference is not None:
        match_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        send_result_message = match_message.reply
        match_embed = match_message.embeds[0]
        teams = [match_embed.fields[0].name, match_embed.fields[1].name]
        players = [match_embed.fields[0].value, match_embed.fields[1].value]        
    else:
        send_channel = ctx.guild.get_channel(chn.get_redirect_channel(ctx.channel.id))
        send_result_message = send_channel.send
        mentions = parsing.get_all_mentions_in_order(ctx, args)
        if len(mentions) != 2:
            await ctx.send("Error: `!result` must be either sent in reply to a"
                           " `!match` message, or include mentions of two teams"
                           " (users or roles)")
            return
        for i, team in enumerate(mentions):
            emoji = f'{i+1}\N{COMBINING ENCLOSING KEYCAP} '
            if isinstance(team, Member):
                teams[i] = emoji
                players[i] = team.mention
            elif isinstance(team, Role):
                teams[i] = emoji + team.name
                players[i] = '\n'.join(m.mention for m in team.members)
            else:
                await ctx.send(f"Error: teams must be mentioned by role or user "
                               f"({team} is {type(team)}")
                return

    result_dict, result_str = parsing.parse_results(' '.join(args))
    
    round_diff = 0
    games_won = [0, 0, 0] # Tiess, team 1 wins, team 2 wins
    for r in result_dict:
        round_diff += r['score'][0] - r['score'][1]
        games_won[r['winner']] += 1 # r['winner'] is 0 if tie, 1 if t1, 2 if t2

    if games_won[1] > games_won[2]:
        winner_emote = "1\N{COMBINING ENCLOSING KEYCAP}"
        loser_emote = "2\N{COMBINING ENCLOSING KEYCAP}"
        footertext = teams[0][3:] + " wins"
        footericon = "https://twemoji.maxcdn.com/v/latest/72x72/31-20e3.png"
    elif games_won[2] > games_won[1]:
        winner_emote = "2\N{COMBINING ENCLOSING KEYCAP}"
        loser_emote = "1\N{COMBINING ENCLOSING KEYCAP}"
        footertext = teams[1][3:] + " wins"
        footericon = "https://twemoji.maxcdn.com/v/latest/72x72/32-20e3.png"
    elif games_won[1] == games_won[2]:
        winner_emote, loser_emote = None, None
        footertext = "Match tied"
        footericon = "https://twemoji.maxcdn.com/v/latest/72x72/1faa2.png"

    result_embed = Embed(title="**Match Result**", description='', colour=Colour.green())
    result_embed.description = result_str
    result_embed.add_field(name=f"{teams[0]} ({round_diff:+})", value=players[0]) # Round diff is (team 1 score - team 2 score)
    result_embed.add_field(name=f"{teams[1]} ({-round_diff:+})", value=players[1])
    result_embed.set_footer(text=footertext, icon_url=footericon)
    await send_result_message(embed=result_embed)

    # If there's a winner, award points to users that made correct predictions
    if winner_emote is not None and match_message is not None:
        # 'correct' is a set of users that reacted with the emote of the winner
        # 'incorrect' is a set of users that reacted with the emote of the loser
        correct, incorrect = set(), set()
        for emote, users in zip((winner_emote, loser_emote),
                                (correct, incorrect)):
            # Get the reaction object of this emote
            reaction = utils.get(match_message.reactions, emoji=emote)
            # Iterate through everyone who used this emote
            async for user in reaction.users():
                # Exclude anyone involved in this match
                if user.mention not in players[0] + players[1]:
                    users.add(user)

        all_reactors = set().union(correct, incorrect)
        correct = correct - incorrect # Exclude users that also reacted incorrectly

        if bool(all_reactors): # If there's somebody who reacted with one of the winner/loser emotes
            correct_ids = [user.id for user in correct]
            ldb.increment(match_message.channel.id, *correct_ids)

            # Anyone who voted will be mentioned
            await match_message.reply(ldb.get_message(match_message.channel.id),
                                      allowed_mentions=AllowedMentions(users=list(all_reactors)))

###############################################################################

# VETO COMMAND
#@bot.command()
#async def veto(ctx, team1: Union[Role, Member], team2: Union[Role, Member]):
#    map_pool = {"Cobblestone": 'de_cbble',
#                "Inferno": 'de_inferno',
#                "Nuke": 'de_nuke',
#                "Overpass": 'de_overpass',
#                "Shortdust": 'de_shortdust',
#                "Train": 'de_train',
#                "Vertigo": 'de_vertigo'}
#    chosen_maps = []
#    
#    veto = [[0, 'ban'], 
#            [1, 'ban'],
#            [0, 'pick'], [1, 'pick starting side'],
#            [1, 'pick'], [0, 'pick starting side'],
#            [0, 'ban'], 
#            [1, 'ban']]
#    
#    remaining_maps = {f"{i+1}\N{COMBINING ENCLOSING KEYCAP}": m for i, m in enumerate(map_pool.keys())}
#
#    team_names = ["", ""]
#    team_users = [[], []]
#    team_mentions = ["", ""]
#    for i, t in enumerate([team1, team2]):
#        team_mentions[i] = t.mention
#        if isinstance(t, Role):
#            team_users[i] = t.members
#            team_names[i] = t.name
#        elif isinstance(t, Member):
#            team_users[i].append(t)
#            team_names[i] = t.display_name
#            
#    # Set the initial parameters
#    active_team = 0  
#    mode = 'ban'
#    
#    def generate_veto_embed(log, footer=True):
#        # First generate the string displaying the remaining maps:
#        maps_display = ""
#        for emoji, mapname in remaining_maps.items():
#            maps_display += f"{emoji} {mapname}\n"
#            
#        title = "**Match veto**"
#        header = f"{team_mentions[0]} vs {team_mentions[1]}\n\n"
#        turn = f"{team_names[active_team]} to {mode}"
#    
#        embed = Embed(title=title,
#                     description=header+maps_display+log)
#        if footer:
#            embed.set_footer(text=turn)
#        return embed
#        
#    # Send the initial message
#    log="\n"
#    veto_embed = generate_veto_embed(log, footer=False)
#    veto_message = await ctx.send(embed=veto_embed)
#    # Add reactions for all the maps
#    for emoji in remaining_maps.keys():
#        await veto_message.add_reaction(emoji)
#    
#    def check_for_veto(reaction, user):
#        return (user in team_users[active_team] 
#                and str(reaction.emoji) in remaining_maps.keys()
#                and reaction.message == veto_message)
#    
#    sides_emoji = {"\N{REGIONAL INDICATOR SYMBOL LETTER T}": 'T',
#                   "\N{REGIONAL INDICATOR SYMBOL LETTER C}": 'CT'}
#    
#    def check_for_sides(reaction, user):
#        return (user in team_users[active_team] 
#                and str(reaction.emoji) in sides_emoji.keys()
#                and reaction.message == veto_message)
#        
#    for active_team, mode in veto:
#        if mode == 'pick' or mode == 'ban':
#            await veto_message.edit(embed=generate_veto_embed(log))
#            # Wait for user to react
#            # On reaction, continue if check_for_veto returns true
#            reaction, user = await bot.wait_for('reaction_add', check=check_for_veto)
#            # Remove all of those reactions
#            await veto_message.clear_reaction(reaction.emoji)
#            # Remove the map corresponding to that reaction
#            selected_map = remaining_maps.pop(str(reaction.emoji))
#            if mode == 'pick':
#                log += f"**{team_names[active_team]} picked {selected_map}\n**"
#            elif mode == 'ban':
#                log += f"{team_names[active_team]} banned {selected_map}\n"
#        if mode == 'pick starting side':
#            await veto_message.clear_reactions()
#            for emoji in sides_emoji.keys():
#                await veto_message.add_reaction(emoji)
#            await veto_message.edit(embed=generate_veto_embed(log))
#            # Wait for user to react
#            # On reaction, continue if check_for_sides returns true
#            reaction, user = await bot.wait_for('reaction_add', check=check_for_sides)
#            chosen_side = sides_emoji[str(reaction.emoji)]
#            log += f"{team_names[active_team]} starting as {chosen_side}\n"
#            # Remove all of those reactions and replace with map selects
#            await veto_message.clear_reactions()
#            for emoji in remaining_maps.keys():
#                await veto_message.add_reaction(emoji)
#    
#    final_map_emoji = list(remaining_maps.keys())[0]
#    await veto_message.clear_reaction(final_map_emoji)    
#    selected_map = remaining_maps.pop(final_map_emoji)
#    log += f"**{selected_map} was left over**"
#    await veto_message.edit(embed=generate_veto_embed(log[1:], footer=False))

@bot.command()
async def veto(ctx, team1: Union[Role, Member], team2: Union[Role, Member]):
    map_pool = [Map('Cobblestone', 'de_cbble'),
                Map('Inferno', 'de_inferno'),
                Map('Nuke', 'de_nuke'),
                Map('Overpass', 'de_overpass'),
                Map('Shortdust', 'de_shortdust'),
                Map('Train', 'de_train'),
                Map('Vertigo', 'de_vertigo')]
    team1 = Team(team1)
    team2 = Team(team2)
    embed = menus.VetoMenu(team1, team2, map_pool)
    await embed.send(ctx)
    while embed.remaining_options:
        reaction, user = await bot.wait_for('reaction_add', check=embed.check_reaction)
        await embed.on_reaction(reaction, user)        

@bot.command()
async def teams(ctx, captain1: Member, captain2: Member, *players):
    players_users = []
    for player in players:
        if isinstance(player, Member):
            players_users.append(player)
        else:
            userid = parsing.convert_mention_into_id(player)
            user = bot.get_user(userid)
            players_users.append(user)
    
    embed = menus.PickTeamsMenu(captain1, captain2, players_users)
    await embed.send(ctx)
    while embed.remaining_options:
        reaction, user = await bot.wait_for('reaction_add', check=embed.check_reaction)
        await embed.on_reaction(reaction, user)
        
        
###############################################################################

# LEADERBOARD COMMAND
@bot.command()
async def leaderboard2(ctx, *args):
    args = list(args)
    if len(ctx.message.channel_mentions) == 0:
        leaderboard_channel_id = ctx.channel.id
    elif len(ctx.message.channel_mentions) == 1:
        leaderboard_channel_id = ctx.message.channel_mentions[0].id
        args.remove(ctx.message.channel_mentions[0].mention)
    else:
        await ctx.send("Error: expected 0 or 1 channel mentions")
        return
    if ctx.author.guild_permissions.manage_channels:
        if len(ctx.message.mentions) == 1:
            user = ctx.message.mentions[0]
            args.remove(user.mention)
        elif len(ctx.message.mentions) > 1:
            await ctx.send("Error: expected 0 or 1 user mentions")
            return
        if "add" in args:
            # This keyword can be used to add a new row, or add points to an
            # existing entry. See leaderboards.add_row for why (it's all done
            # in sqlite rather than python)
            args.remove("add")
            if args:
                points = args[-1]
            else:
                points = 0
            ldb.add_row(leaderboard_channel_id, user.id, points)
            await ctx.send("Added row: <#{}> <@{}> {}pts\n*If row existed, points were added to that row's points*".format(leaderboard_channel_id, user.id, points))
            return
        elif "del" in args:
            ldb.delete_row(leaderboard_channel_id, user.id)
            await ctx.send("Deleted row: <#{}> <@{}>".format(leaderboard_channel_id, user.id))
            return
        elif "set" in args:
            args.remove("set")
            points = args[-1]
            ldb.set_points(leaderboard_channel_id, user.id, points)
            await ctx.send("Set points: <#{}> <@{}> {}pts".format(leaderboard_channel_id, user.id, points))
            return
    await ctx.send(ldb.get_message(leaderboard_channel_id), allowed_mentions=AllowedMentions(users=False))


###############################################################################
###############################################################################

with open('bot_token.txt') as f:
    bot_token = f.read().strip()
bot.run(bot_token)
