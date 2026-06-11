import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime, timedelta

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_coins(self, user_id, amount):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute(
                "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()

    async def create_table(self):
        async with aiosqlite.connect("economy.db") as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                coins INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                last_daily TEXT
            )
            """)
            await db.commit()

    async def cog_load(self):
        await self.create_table()
        print("Economy cog loaded")

    async def get_user(self, user_id):
        async with aiosqlite.connect("economy.db") as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = await cursor.fetchone()

            if user is None:
                await db.execute(
                    "INSERT INTO users (user_id, coins, messages) VALUES (?, ?, ?)",
                    (user_id, 100, 0)
                )               
                await db.commit()
                return (user_id, 100, 0, None)

            return user

    @app_commands.command(name="balance", description="Check your balance")
    async def balance(self, interaction: discord.Interaction):
        user = await self.get_user(interaction.user.id)

        embed = discord.Embed(
            title="💰 Balance",
            description=f"You have **{user[1]}** coins.",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: discord.Interaction):

        await self.get_user(interaction.user.id)
        async with aiosqlite.connect("economy.db") as db:

            cursor = await db.execute(
                "SELECT last_daily FROM users WHERE user_id = ?",
                (interaction.user.id,)
            )

            result = await cursor.fetchone()

            now = datetime.utcnow()

            if result and result[0]:

                last_daily = datetime.fromisoformat(result[0])

                if now - last_daily < timedelta(hours=24):

                    remaining = timedelta(hours=24) - (now - last_daily)

                    hours = remaining.seconds // 3600
                    minutes = (remaining.seconds % 3600) // 60

                    await interaction.response.send_message(
                        f"⏳ You already claimed your daily reward.\n"
                        f"Try again in **{hours}h {minutes}m**.",
                        ephemeral=True
                    )
                    return

            reward = 500

            await db.execute(
                """
                UPDATE users
                SET coins = coins + ?, last_daily = ?
                WHERE user_id = ?
                """,
                (
                    reward,
                    now.isoformat(),
                    interaction.user.id
                )
            )

            await db.commit()

            embed = discord.Embed(
                title="🎁 Daily Reward",
                description=f"You received **{reward} coins**!",
                color=discord.Color.green()
            )

            await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        async with aiosqlite.connect("economy.db") as db:

            await self.get_user(message.author.id)

            await db.execute(
                """
                UPDATE users
                SET messages = messages + 1
                WHERE user_id = ?
                """,
                (message.author.id,)
            )

            cursor = await db.execute(
                """
                SELECT messages
                FROM users
                WHERE user_id = ?
                """,
                (message.author.id,)
            )

            data = await cursor.fetchone()

            messages = data[0]

            if messages % 100 == 0:

                await db.execute(
                    """
                    UPDATE users
                    SET coins = coins + 100
                    WHERE user_id = ?
                    """,
                    (message.author.id,)
                )

            await db.commit()

    @app_commands.command(name="profile", description="View your profile")
    async def profile(self, interaction: discord.Interaction):

        await self.get_user(interaction.user.id)

        async with aiosqlite.connect("economy.db") as db:

            cursor = await db.execute(
                """
                SELECT coins, messages
                FROM users
                WHERE user_id = ?
                """,
                (interaction.user.id,)
            )

            data = await cursor.fetchone()

            embed = discord.Embed(
                title=f"{interaction.user.name}'s Profile",
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="💰 Coins",
                value=data[0]
            )

            embed.add_field(
                name="💬 Messages",
                value=data[1]
            )

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shop", description="View the server shop")
    async def shop(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🛒 Crescent Shop",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🎞️ GIF Permission",
            value="100 Coins",
            inline=False
        )

        embed.add_field(
            name="🎨 Custom Role Color",
            value="200 Coins",
            inline=False
        )

        embed.add_field(
            name="🏷️ Server Tag",
            value="300 Coins",
            inline=False
        )

        embed.set_footer(
            text="Use /buy <item> to purchase an item"
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))