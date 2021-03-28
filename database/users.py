from aiosqlite import Connection
db: Connection


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

async def add_steam64_id(user_id, steam64_id):
    await db.execute(
        "INSERT OR REPLACE INTO users(user_id, steam64_id)"
        "   VALUES(?, ?)",
        (user_id, steam64_id)
    )

async def add_steam64_ids(users):
    await db.executemany(
        "INSERT OR REPLACE INTO users(user_id, steam64_id)"
        " VALUES (?, ?)",
        ((discord, steam) for discord,steam in users.items())
    )

async def get_steam64_id(user_id):
    async with db.execute(
                "SELECT steam64_id FROM users"
                "   WHERE user_id =?",
                (user_id,)
            ) as cursor:
        data = await cursor.fetchone()
    if not data:
        raise ValueError(f"No steamid found for user_id {user_id}")
    else:
        return data[0]

async def get_steam64_ids(user_ids):
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
        raise ValueError(f"No steam64_id found for user_ids {not_found_users}")
    else:
        return d

