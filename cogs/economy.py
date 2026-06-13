import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime, timedelta
import asyncio
from discord.ui import View, Select
import os
from dotenv import load_dotenv

load_dotenv()

OWNER_ID = int(os.getenv("OWNER_ID"))
GIF_ROLE_ID =1514647359445799072

class ShopDropdown(Select):
    def __init__(self):

        options = [
            discord.SelectOption(
                label="GIF Permission",
                emoji="🎞️",
                description="100 Coins"
            ),
            discord.SelectOption(
                label="Server Tag",
                emoji="🏷️",
                description="500 Coins"
            ),
            discord.SelectOption(
                label="Color Roles",
                emoji="🎨",
                description="600-1000 Coins"
            )
        ]

        super().__init__(
            placeholder="Select an item...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if self.values[0] == "GIF Permission":

            cog = interaction.client.get_cog("Economy")

            user = await cog.get_user(interaction.user.id)

            if user[1] < 100:
                await interaction.response.send_message(
                    "❌ You need 100 coins to buy GIF Permission.",
                    ephemeral=True
                )
                return

            role = interaction.guild.get_role(GIF_ROLE_ID)

            if role is None:
                await interaction.response.send_message(
                    "❌ GIF role not found.",
                    ephemeral=True
                )
                return

            if role in interaction.user.roles:
                await interaction.response.send_message(
                    "❌ You already have GIF Permission.",
                    ephemeral=True
                )
                return

            await cog.add_coins(interaction.user.id, -100)

            await interaction.user.add_roles(role)

            await interaction.response.send_message(
                "🎞️ GIF Permission activated for 2 minutes!",
                ephemeral=True
            )

            await asyncio.sleep(120)

            await interaction.user.remove_roles(role)


        elif self.values[0] == "Server Tag":

            await interaction.response.send_modal(
                TagModal()
            )

        elif self.values[0] == "Color Roles":

            await interaction.response.send_message(
                "🎨 Color Roles selected.\nCost: 600-1000 Coins",
                ephemeral=True
            )


class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ShopDropdown())

class TagModal(discord.ui.Modal, title="Create Server Tag"):

    tag = discord.ui.TextInput(
        label="Enter a 4-letter tag",
        placeholder="GOAT",
        min_length=4,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):

        tag = self.tag.value.upper()

        cog = interaction.client.get_cog("Economy")

        user = await cog.get_user(interaction.user.id)

        if user[1] < 500:
            await interaction.response.send_message(
                "❌ You need 500 coins.",
                ephemeral=True
            )
            return

        try:

            old_name = interaction.user.display_name

            await cog.add_coins(
                interaction.user.id,
                -500
            )

            await interaction.user.edit(
                nick=f"[{tag}] {old_name}"
            )

            await interaction.response.send_message(
                f"✅ Tag **{tag}** activated for 4 hours!",
                ephemeral=True
            )

            member = interaction.guild.get_member(interaction.user.id)

            await asyncio.sleep(20)

            try:

                if member.nick and member.nick.startswith(f"[{tag}] "):

                    original_name = member.nick[len(f"[{tag}] "):]

                    await member.edit(
                        nick=original_name
                    )

            except Exception as e:
                print(e)

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ I don't have permission to change nicknames.",
                ephemeral=True
            )

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

    @app_commands.command(name="addcoins", description="Add coins")
    async def addcoins(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int
    ):

        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "❌ Owner only command.",
                ephemeral=True
            )
            return

        await self.get_user(member.id)
        await self.add_coins(member.id, amount)

        await interaction.response.send_message(
            f"✅ Added {amount} coins to {member.mention}"
        )

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

            # Increase message count
            await db.execute(
                """
                UPDATE users
                SET messages = messages + 1
                WHERE user_id = ?
                """,
                (message.author.id,)
            )

            # IMPORTANT: Save the update first
            await db.commit()

            # Get updated message count
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

            # Reward every 100 messages
            if messages % 100 == 0:

                reward = 100

                await db.execute(
                    """
                    UPDATE users
                    SET coins = coins + ?
                    WHERE user_id = ?
                    """,
                    (reward, message.author.id)
                )

                await db.commit()

                await message.channel.send(
                    f"🎉 {message.author.mention} has reached **{messages} messages** and earned **{reward} coins!** 💰"
                )
                
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
            description="Select an item below.",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="🎞️ GIF Permission",
            value="100 Coins | 2 Minutes",
            inline=False
        )

        embed.add_field(
            name="🏷️ Server Tag",
            value="500 Coins | 4 Hours",
            inline=False
        )

        embed.add_field(
            name="🎨 Color Roles",
            value="600-1000 Coins | 24 Hours",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            view=ShopView()
        )
async def setup(bot):
    await bot.add_cog(Economy(bot))