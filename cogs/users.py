import discord.ext.commands as cmds
from steam import steamid
from cogs import Cog
import parsing

class UsersCog(Cog, name="User database commands"):
    @cmds.command()
    async def users(self, ctx):
        if ctx.author.guild_permissions.manage_channels:
            s = await ctx.bot.db.users.display()
            await ctx.send(s)

    @cmds.command()
    async def steam(self, ctx, *args):
        """Link your Steam and Discord accounts for server configuration."""
        args = list(args)
        mentions = parsing.get_all_mentions_in_order(ctx, args, pop=True)
        if len(mentions) == 1:
            user = mentions[0]
        else:
            user = ctx.author
        if len(args) == 1:
            profile_url = args[0]
            if "steamcommunity.com" in profile_url:
                steam64_id = steamid.steam64_from_url(profile_url)
                await ctx.bot.db.users.add_steam64_id(user.id, steam64_id)
                await ctx.send(f"Linked {user.mention} to <{profile_url}>")
            else:
                await ctx.send(f"Error: link not recognised as a steam profile link ({profile_url})")
        elif len(args) == 0:
            try:
                steam64_id = await ctx.bot.db.users.get_steam64_id(user.id)
                await ctx.send(f"{user.mention}'s steam64_id is {steam64_id}")
            except:
                await ctx.send(f"No steam64_id stored for {user.mention}")
        else:
            await ctx.send(f"Got too many arguments (expected 0, 1 or 2, got {len(args)})")


def setup(bot):
    bot.add_cog(UsersCog(bot))
