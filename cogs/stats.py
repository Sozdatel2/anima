import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from datetime import datetime, timedelta, timezone
import json
import asyncio
from pathlib import Path

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DATA_PATH = Path(__file__).parent.parent / "data" / "server_stats.json"
        self.DATA_PATH.parent.mkdir(exist_ok=True)
        self.data = self.load_data()
        self.bot.loop.create_task(self.update_stats_loop())

    def load_data(self):
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"messages": {}}

    def save_data(self):
        with open(self.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    async def update_stats_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")

            total_messages = 0
            week_messages = 0
            for day, count in self.data["messages"].items():
                total_messages += count
                if day >= week_ago:
                    week_messages += count

            self.data["total_messages"] = total_messages
            self.data["week_messages"] = week_messages
            self.data["last_update"] = now.isoformat()
            self.save_data()

            await asyncio.sleep(3600)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in self.data["messages"]:
            self.data["messages"][today] = 0
        self.data["messages"][today] += 1
        self.save_data()

    @nextcord.slash_command(name="ping", description="Проверить задержку бота")
    async def ping_slash(self, interaction: Interaction):
        """／ Пинг бота．"""
        latency = round(self.bot.latency * 1000)
        embed = nextcord.Embed(
            title="／ Пинг．",
            description=f"Задержка： **{latency}** мс",
            color=0x00FF00 if latency < 100 else (0xFFA500 if latency < 300 else 0xFF0000)
        )
        await interaction.response.send_message(embed=embed)

    @commands.command(name="ping", description="Проверить задержку бота")
    async def ping_prefix(self, ctx):
        await self.ping_command(ctx)

    async def ping_command(self, context):
        latency = round(self.bot.latency * 1000)
        embed = nextcord.Embed(
            title="／ Пинг．",
            description=f"Задержка： **{latency}** мс",
            color=0x00FF00 if latency < 100 else (0xFFA500 if latency < 300 else 0xFF0000)
        )
        if isinstance(context, Interaction):
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)

    @nextcord.slash_command(name="avatar", description="Показать аватарку пользователя")
    async def avatar_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(
            description="Пользователь (по умолчанию — вы)",
            required=False
        )
    ):
        """／ Аватарка．"""
        if member is None:
            member = interaction.user

        embed = nextcord.Embed(
            title=f"／ Аватарка {member.name}．",
            color=member.color
        )
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Запросил： {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    @commands.command(name="avatar", aliases=["av"], description="Показать аватарку пользователя")
    async def avatar_prefix(self, ctx, member: nextcord.Member = None):
        if member is None:
            member = ctx.author

        embed = nextcord.Embed(
            title=f"／ Аватарка {member.name}．",
            color=member.color
        )
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Запросил： {ctx.author.display_name}")

        await ctx.send(embed=embed)

    @nextcord.slash_command(name="stats", description="Показать статистику сервера по сообщениям")
    async def stats_slash(self, interaction: Interaction):
        """／ Статистика сервера．"""
        await self.stats_command(interaction)

    @commands.command(name="stats", description="Показать статистику сервера по сообщениям")
    async def stats_prefix(self, ctx):
        await self.stats_command(ctx)

    async def stats_command(self, context):
        guild = context.guild if hasattr(context, 'guild') else context.guild
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        today_messages = self.data["messages"].get(today, 0)
        week_messages = 0
        total_messages = 0

        for day, count in self.data["messages"].items():
            total_messages += count
            if day >= week_ago:
                week_messages += count

        bots = len(guild.bots)
        users = guild.member_count - bots

        embed = nextcord.Embed(
            title="／ Статистика сервера по сообщениям．",
            color=0x2B2D31,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name="💬 Сообщения",
            value=f"За сегодня： **{today_messages}**\nЗа неделю： **{week_messages}**\nВсего： **{total_messages}**",
            inline=True
        )

        embed.set_footer(text=f"ID： {guild.id}")

        if isinstance(context, Interaction):
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)

def setup(bot):
    bot.add_cog(Stats(bot))