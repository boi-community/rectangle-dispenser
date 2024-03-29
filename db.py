import asqlite


async def create_table(table: str, keys: tuple):
    """
    Creates a table if it does not exist.
    - table: String corresponding to a table in the SQLite database.
    - keys: Tuple of keys for new table.
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            # Quick crash course:
            # - We're using SQLite 3 via an async wrapper, asqlite
            # - Parenthesis are needed to properly use these values because of the quirks associated with being async
            # - [0] is needed to get the actual result in this case
            does_exist = (
                await (
                    await cursor.execute(
                        f"SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table}'"
                    )
                ).fetchone()
            )[0]
            if not does_exist:
                await cursor.execute(f"CREATE TABLE {table} {keys}")
                await conn.commit()


async def drop_table(table: str):
    """
    Drops a table from the database.
    - table: String corresponding to a table in the SQLite database.
    Returns True if table was successfully dropped.
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute(f"DROP TABLE {table}")
                await conn.commit()
                return True
            except asqlite.OperationalError:
                return False


async def insert(table: str, values: tuple or str, replacements: tuple = None):
    """
    Inserts values into a table.
    - table: String corresponding to a table in the SQLite database.
    - values: Tuple of values to insert into the table.
    - replacements: Optional tuple. Used if values specified are for replacement for advanced operations.
    Returns False if data could not be inserted, True if inserted
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"INSERT INTO {table} VALUES {values}", replacements)
            await conn.commit()


async def remove(table: str, exp: str):
    """
    Removes values from a table.
    - table: String corresponding to a table in the SQLite database.
    - exp: Expression for deletion.
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"DELETE FROM {table} WHERE {exp}")
            await conn.commit()


async def update(table: str, exp: str):
    """
    Updates value in the table.
    - table: String corresponding to a table in the SQLite database.
    - exp: Expression for updating.
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"UPDATE {table} SET {exp}")
            await conn.commit()


async def query(query: str):
    """
    Queries from the database in read-only mode.
    - query: String containing the query for the database.
    Returns query as a tuple if multiple variables were queried, or raw query otherwise
    """
    async with asqlite.connect(
        "file:./rectangle-dispenser.db?mode=ro", uri=True
    ) as conn:
        async with conn.cursor() as cursor:
            result = await (await cursor.execute(query)).fetchone()
            if not result:
                return None
            result = tuple(result)
            if len(result) == 1:
                result = result[0]
            return result


async def queryall(query: str):
    """
    Queries from the database in read-only mode.
    - query: String containing the query for the database.
    Returns a list of matching queries as tuples if multiple variables were queried, or raw list of matching queries otherwise
    """
    async with asqlite.connect(
        "file:./rectangle-dispenser.db?mode=ro", uri=True
    ) as conn:
        async with conn.cursor() as cursor:
            result = await (await cursor.execute(query)).fetchall()
            if not result:
                return None
            result = [tuple(elem) for elem in result]
            for i in range(len(result)):
                if len(result[i]) == 1:
                    result[i] = result[i][0]
            return result

async def query_rw(query: str):
    """
    Queries from the database.
    - query: String containing the query for the database.
    Returns query as a tuple if multiple variables were queried, or raw query otherwise
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            result = await (await cursor.execute(query)).fetchone()
            if not result:
                return None
            result = tuple(result)
            if len(result) == 1:
                result = result[0]
            return result


async def queryall_rw(query: str):
    """
    Queries from the database.
    - query: String containing the query for the database.
    Returns a list of matching queries as tuples if multiple variables were queried, or raw list of matching queries otherwise
    """
    async with asqlite.connect("rectangle-dispenser.db") as conn:
        async with conn.cursor() as cursor:
            result = await (await cursor.execute(query)).fetchall()
            if not result:
                return None
            result = [tuple(elem) for elem in result]
            for i in range(len(result)):
                if len(result[i]) == 1:
                    result[i] = result[i][0]
            return result
