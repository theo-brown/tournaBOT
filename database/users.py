from aiosqlite import Connection
from typing import Union, Iterable, Mapping

db: Connection


class SteamIDNotFoundError(LookupError):
    def __init__(self, message: str, user_ids: Iterable[int]):
        super().__init__(message)
        self.user_ids = user_ids


async def create():
    await db.execute(
        "CREATE TABLE IF NOT EXISTS users("
        "   user_id INT PRIMARY KEY,"
        "   steam64_id INT"
        ")"
    )


async def clear():
    await db.execute("DELETE FROM users")


async def display():
    s = "user_id\t\t\tsteam64_id"

    async with db.execute("SELECT * FROM users") as cursor:
        async for uid, steam in cursor:
            s += f"\n{uid}\t{steam}"

    return s


async def add_steam64_ids(users: Mapping[int, int]):
    await db.executemany(
        "INSERT OR REPLACE INTO users(user_id, steam64_id)"
        " VALUES (?, ?)",
        ((discord_id, steam_id) for discord_id, steam_id in users.items())
    )


async def get_steam64_ids(user_ids: Union[Iterable[int], int]):
    if isinstance(user_ids, int):
        user_ids = [user_ids]
    parameters = ", ".join(['?']*len(user_ids))
    async with db.execute(
                f"SELECT user_id, steam64_id FROM users"
                f"  WHERE user_id IN ({parameters})",
                user_ids
            ) as cursor:
        d = {user_id: steam64_id async for (user_id, steam64_id) in cursor}
    # Check that all users were found in the table
    not_found_users = []
    for user_id in user_ids:
        if user_id not in d.keys():
            not_found_users.append(user_id)
    if not_found_users:
        raise SteamIDNotFoundError(f"No steam64_id found for user_id(s) {not_found_users}", not_found_users)
    if len(d) == 1:
        return d[user_ids[0]]
    else:
        return d
