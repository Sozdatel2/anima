## Импорты библиотек
import nextcord
import datetime
import humanfriendly
import json
import asyncio
from pathlib import Path

## Импорты из файлов/библиотек
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.LOG_CHANNEL_ID = 1234596840008323162
        self.bot.loop.create_task(self.check_tempbans())

    async def log_action(self, title: str, fields: list = None):
        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
        if not channel:
            return
        embed = Embed(
            title=f"／ {title}．",
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await channel.send(embed=embed)

    async def _tempban_command(self, context, member: nextcord.Member, time: str, reason: str):
        """Основной метод для временного бана (вызывается из нокт)"""
        try:
            time_seconds = humanfriendly.parse_timespan(time)
            unban_at = datetime.datetime.now(datetime.timezone.utc).timestamp() + time_seconds

            await member.ban(reason=f'{context.author.name if context else "Система"}: {reason}')

            tempban_path = Path(__file__).parent.parent / "data" / "tempbans.json"
            tempban_path.parent.mkdir(exist_ok=True)

            try:
                with open(tempban_path, "r", encoding="utf-8") as f:
                    tempbans = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                tempbans = {}

            user_id = str(member.id)
            tempbans[user_id] = {
                "unban_at": unban_at,
                "guild_id": member.guild.id,
                "reason": reason,
                "moderator": context.author.name if context else "Система"
            }

            with open(tempban_path, "w", encoding="utf-8") as f:
                json.dump(tempbans, f, indent=2, ensure_ascii=False)

            time_str = humanfriendly.format_timespan(time_seconds)
            await self.log_action(
                title="Временный бан",
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Модератор", context.author.mention if context else "Система", True),
                    ("Длительность", time_str, True),
                    ("Причина", reason, False)
                ]
            )

            return True
        except humanfriendly.InvalidTimespan:
            return False

    async def check_tempbans(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            tempban_path = Path(__file__).parent.parent / "data" / "tempbans.json"

            try:
                with open(tempban_path, "r", encoding="utf-8") as f:
                    tempbans = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                tempbans = {}

            to_unban = []
            for user_id, data in tempbans.items():
                if data["unban_at"] <= now:
                    to_unban.append(user_id)

            for user_id in to_unban:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    guild = self.bot.get_guild(tempbans[user_id]["guild_id"])
                    if guild:
                        await guild.unban(user)
                        tempbans.pop(user_id, None)

                        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
                        if channel:
                            embed = Embed(
                                title="／ Авторазбан．",
                                description=f"Пользователь **{user.name}** автоматически разбанен",
                                timestamp=datetime.datetime.now(datetime.timezone.utc)
                            )
                            await channel.send(embed=embed)
                except:
                    tempbans.pop(user_id, None)

            with open(tempban_path, "w", encoding="utf-8") as f:
                json.dump(tempbans, f, indent=2, ensure_ascii=False)

            await asyncio.sleep(3600)

    @nextcord.slash_command(name="mute", description="Выдать мут пользователю (timeout)")
    @commands.has_permissions(moderate_members=True)
    async def mute_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Участник для мута", required=True),
        time: str = SlashOption(description="Время (например: 10m, 1h, 1d)", required=True),
        reason: str = SlashOption(description="Причина мута", required=False, default="Не указана")
    ):
        await self._mute_command(interaction, member, time, reason)

    @commands.command(name="mute", description="Выдать мут пользователю на сервере (timeout)")
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx, member: nextcord.Member, time: str, *, reason: str = "Не указана"):
        await self._mute_command(ctx, member, time, reason)

    async def _mute_command(self, context, member: nextcord.Member, time: str, reason: str):
        try:
            time_seconds = humanfriendly.parse_timespan(time)
            timeout_end = nextcord.utils.utcnow() + datetime.timedelta(seconds=time_seconds)
            timestamp_formatted = int(timeout_end.timestamp())

            await member.edit(
                timeout=timeout_end,
                reason=f'{context.author.name if context else "Система"} | {reason}'
            )

            emb = nextcord.Embed(
                title="／ Выдача мута．",
                description="Пользователю был выдан мут на сервере．"
            )
            emb.add_field(name="Замьючен：", value=f"{member.mention} | **{member.name}**", inline=True)
            emb.add_field(name="Модератор：", value=f"{context.author.mention if context else 'Система'} | **{context.author.name if context else 'Система'}**", inline=True)
            emb.add_field(name="Мут истекает：", value=f"<t:{timestamp_formatted}:R>", inline=True)
            emb.add_field(name="Причина：", value=f"**{reason}**", inline=False)

            await self.log_action(
                title="Выдача мута",
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Модератор", context.author.mention if context else "Система", True),
                    ("Длительность", humanfriendly.format_timespan(time_seconds), True),
                    ("Причина", reason, False)
                ]
            )

            if isinstance(context, Interaction):
                await context.response.send_message(embed=emb)
            else:
                await context.send(embed=emb)

        except humanfriendly.InvalidTimespan:
            error_emb = nextcord.Embed(
                description="❌ Некорректный формат времени．Используйте： `10s`, `5m`, `1h`, `1d`"
            )
            if isinstance(context, Interaction):
                await context.response.send_message(embed=error_emb, ephemeral=True)
            else:
                await context.send(embed=error_emb)

    @nextcord.slash_command(name="unmute", description="Снять мут с пользователя")
    @commands.has_permissions(moderate_members=True)
    async def unmute_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Участник для размута", required=True)
    ):
        await self._unmute_command(interaction, member)

    @commands.command(name="unmute", description="Снять мут с пользователя на сервере")
    @commands.has_permissions(moderate_members=True)
    async def unmute_prefix(self, ctx, member: nextcord.Member):
        await self._unmute_command(ctx, member)

    async def _unmute_command(self, context, member: nextcord.Member):
        await member.edit(timeout=None)

        emb = nextcord.Embed(
            title="／ Снятие мута．",
            description="С пользователя был снят мут．"
        )
        emb.add_field(name="Размьючен：", value=f"{member.mention} | **{member.name}**", inline=True)
        emb.add_field(name="Модератор：", value=f"{context.author.mention} | **{context.author.name}**", inline=True)

        await self.log_action(
            title="Снятие мута",
            fields=[
                ("Пользователь", member.mention, True),
                ("Модератор", context.author.mention, True)
            ]
        )

        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)

    @nextcord.slash_command(name="kick", description="Выгнать пользователя с сервера")
    @commands.has_permissions(kick_members=True)
    async def kick_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Участник для кика", required=True),
        reason: str = SlashOption(description="Причина кика", required=False, default="Не указана")
    ):
        await self._kick_command(interaction, member, reason)

    @commands.command(name="kick", description="Выгнать пользователя с сервера")
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx, member: nextcord.Member, *, reason: str = "Не указана"):
        await self._kick_command(ctx, member, reason)

    async def _kick_command(self, context, member: nextcord.Member, reason: str):
        author = context.author
        await member.kick(reason=f'{author.name}: {reason}')

        emb = nextcord.Embed(
            title="／ Участник кикнут．",
            description="Пользователь был успешно кикнут с сервера．"
        )
        emb.add_field(name="Кикнут：", value=f"{member.mention} | **{member.name}**", inline=True)
        emb.add_field(name="Модератор：", value=f"{author.mention} | **{author.name}**", inline=True)
        emb.add_field(name="Причина：", value=f"**{reason}**", inline=False)

        await self.log_action(
            title="Кик",
            fields=[
                ("Пользователь", member.mention, True),
                ("Модератор", author.mention, True),
                ("Причина", reason, False)
            ]
        )

        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)

def setup(bot):
    bot.add_cog(Moderation(bot))