from motor.motor_asyncio import AsyncIOMotorClient as MongoClient
from bson.json_util import loads,dumps
import aiofiles, aiofiles.os
from os import getenv
from discord.ext import tasks, commands as cmds
from . import users


class MongoCog(cmds.Cog, name='Mongo update script'):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_users = MongoClient(getenv('MONGO_URI')).popskill.user_links
        self.token = None
        self.watch.start()

    @tasks.loop(count=1)
    async def watch(self):
        async with self.mongo_users.watch([{'$match': {'operationType': {'$in': ['insert', 'update', 'replace']}}}],
                                          full_document='updateLookup',
                                          resume_after=self.token) as stream:
            async for change in stream:
                entry = change['fullDocument']
                if 'steam_id' in entry:
                    await users.add_steam64_id(entry['discord_id'], entry['steam_id'])
                self.token = stream.resume_token

    @watch.before_loop
    async def get_token(self):
        try:
            async with aiofiles.open('resume', 'rb') as tokenfile:
                self.token = loads(await tokenfile.read())
        except FileNotFoundError:
            pass  # token is None by default

    @watch.after_loop
    async def store_token(self):
        if self.token is None:
            return

        async with aiofiles.open('resume', 'wb') as tokenfile:
            await tokenfile.write(dumps(self.token))

    @watch.error
    async def log_error(self, error):
        info = await self.bot.application_info()
        await info.owner.send(
            f'**{type(error).__name__}**\n{error}'
        )

    @cmds.command()
    @cmds.is_owner()
    async def update(self, ctx):
        async with ctx.typing():
            await users.add_steam64_ids({
                user['discord_id']: user['steam_id']
                    async for user in self.mongo_users.find() if 'discord_id' in user
            })
        await ctx.send(f'Successfully upserted {len(users_with_steam_ids)} users.')

        # no point resuming after full update
        await aiofiles.os.remove('resume')
        self.watch.restart()
