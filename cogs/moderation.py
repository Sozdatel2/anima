## Импорты библиотек
import nextcord
import datetime
import json
import asyncio
import re
from pathlib import Path

## Импорты из файлов/библиотек
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.LOG_CHANNEL_ID = 1234596840008323162
        self.OWNER_ID = 942776739870933003
        self.bot.loop.create_task(self.check_tempbans())

    async def log_action(self, title: str, fields: list = None, color: int = 0x2B2D31):
        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
        if not channel:
            return
        embed = Embed(
            title=f"／ {title}．",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            color=color
        )
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await channel.send(embed=embed)

    def parse_time(self, time_str: str) -> int:
        if not time_str or time_str.strip() == "":
            return 0

        total_seconds = 0
        time_str = time_str.lower().strip()

        patterns = [
            (r'(\d+)\s*д', 86400),   # дни
            (r'(\d+)\s*ч', 3600),    # часы
            (r'(\d+)\s*м', 60),      # минуты
            (r'(\d+)\s*с', 1),       # секунды
        ]

        for pattern, multiplier in patterns:
            matches = re.findall(pattern, time_str)
            for match in matches:
                total_seconds += int(match) * multiplier

        return total_seconds

    def format_time(self, seconds: int) -> str:
        if seconds <= 0:
            return "0с"

        parts = []
        days = seconds // 86400
        if days:
            parts.append(f"{days}д")
            seconds %= 86400

        hours = seconds // 3600
        if hours:
            parts.append(f"{hours}ч")
            seconds %= 3600

        minutes = seconds // 60
        if minutes:
            parts.append(f"{minutes}м")
            seconds %= 60

        if seconds:
            parts.append(f"{seconds}с")

        return " ".join(parts)

    def _check_target(self, author, member) -> str:
        if author.id == member.id:
            return "❌ Нельзя наказать самого себя!"
        if member.bot:
            return "❌ Нельзя наказать бота!"
        if member.id == self.OWNER_ID:
            return "❌ Нельзя наказать владельца бота!"
        if member.guild_permissions.administrator and author.id != self.OWNER_ID:
            return "❌ Нельзя наказать администратора!"
        return None

    async def _send_error(self, context, message: str):
        embed = Embed(title="／ Ошибка．", description=message)
        if isinstance(context, Interaction):
            await context.response.send_message(embed=embed, ephemeral=True)
        else:
            await context.send(embed=embed)

    async def _apply_tempban(self, member: nextcord.Member, time_seconds: int, reason: str, moderator: str):
        unban_at = datetime.datetime.now(datetime.timezone.utc).timestamp() + time_seconds

        tempban_path = Path(__file__).parent.parent / "data" / "tempbans.json"
        tempban_path.parent.mkdir(exist_ok=True)

        try:
            with open(tempban_path, "r", encoding="utf-8") as f:
                tempbans = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            tempbans = {}

        tempbans[str(member.id)] = {
            "unban_at": unban_at,
            "guild_id": member.guild.id,
            "reason": reason,
            "moderator": moderator
        }

        with open(tempban_path, "w", encoding="utf-8") as f:
            json.dump(tempbans, f, indent=2, ensure_ascii=False)

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

            to_unban = [uid for uid, data in tempbans.items() if data["unban_at"] <= now]

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

    @commands.command(name="ban", description="Забанить пользователя (временно или навсегда)")
    @commands.has_permissions(ban_members=True)
    async def ban_prefix(self, ctx, member: nextcord.Member, *, args: str = ""):
        error = self._check_target(ctx.author, member)
        if error:
            await self._send_error(ctx, error)
            return

        time_str = ""
        reason = args

        time_pattern = re.compile(r'(\d+\s*[дчмс])+', re.IGNORECASE)
        match = time_pattern.search(args)
        if match:
            time_str = match.group()
            reason = args.replace(time_str, "").strip()
            if not reason:
                reason = "Не указана"

        time_seconds = self.parse_time(time_str) if time_str else 0

        if time_seconds > 0:
            await self._ban_command(ctx, member, reason, time_seconds)
        else:
            if time_str:
                await self._send_error(ctx, f"❌ Не удалось распознать время: `{time_str}`\nИспользуйте формат: `7д`, `1д 12ч`, `30м`")
                return
            await self._ban_command(ctx, member, reason, None)

    @nextcord.slash_command(name="ban", description="Забанить пользователя (временно или навсегда)")
    @commands.has_permissions(ban_members=True)
    async def ban_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Участник для бана", required=True),
        time: str = SlashOption(description="Время (7д, 1д 12ч, 30м) — не указывайте для перманентного", required=False),
        reason: str = SlashOption(description="Причина бана", required=False, default="Не указана")
    ):
        error = self._check_target(interaction.user, member)
        if error:
            await self._send_error(interaction, error)
            return

        if time:
            time_seconds = self.parse_time(time)
            if time_seconds > 0:
                await self._ban_command(interaction, member, reason, time_seconds)
            else:
                await self._send_error(interaction, f"❌ Не удалось распознать время: `{time}`\nИспользуйте формат: `7д`, `1д 12ч`, `30м`")
        else:
            await self._ban_command(interaction, member, reason, None)

    async def _ban_command(self, context, member: nextcord.Member, reason: str, time_seconds: int = None):
        author = context.author if hasattr(context, 'author') else context.user

        if time_seconds:
            await member.ban(reason=f'{author.name} (временный): {reason}')
            await self._apply_tempban(member, time_seconds, reason, author.name)

            time_str = self.format_time(time_seconds)
            title = "／ Временный бан．"
            description = f"Пользователь **{member.name}** временно забанен на **{time_str}**"
        else:
            await member.ban(reason=f'{author.name}: {reason}')
            title = "／ Участник забанен．"
            description = f"Пользователь **{member.name}** был забанен на сервере"

        emb = Embed(title=title, description=description)
        emb.add_field(name="Забанен：", value=member.mention, inline=True)
        emb.add_field(name="Модератор：", value=author.mention, inline=True)
        if time_seconds:
            emb.add_field(name="Длительность：", value=f"**{self.format_time(time_seconds)}**", inline=True)
        emb.add_field(name="Причина：", value=f"**{reason}**", inline=False)

        await self.log_action(
            title="Бан" if not time_seconds else "Временный бан",
            fields=[
                ("Пользователь", member.mention, True),
                ("Модератор", author.mention, True),
                ("Длительность", self.format_time(time_seconds) if time_seconds else "Перманентно", True),
                ("Причина", reason, False)
            ],
            color=0xFF0000
        )

        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)

    @commands.command(name="unban", description="Разбанить пользователя по ID")
    @commands.has_permissions(ban_members=True)
    async def unban_prefix(self, ctx, user_id: str):
        await self._unban_command(ctx, user_id)

    @nextcord.slash_command(name="unban", description="Разбанить пользователя по ID")
    @commands.has_permissions(ban_members=True)
    async def unban_slash(
        self,
        interaction: Interaction,
        user_id: str = SlashOption(description="ID пользователя для разбана", required=True)
    ):
        await self._unban_command(interaction, user_id)

    async def _unban_command(self, context, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            guild = context.guild if hasattr(context, 'guild') else context.guild
            await guild.unban(user)

            emb = Embed(
                title="／ Разбан．",
                description=f"Пользователь **{user.name}** был разбанен на сервере"
            )
            emb.add_field(name="Разбанен：", value=f"{user.mention} | **{user.name}**", inline=True)
            author = context.author if hasattr(context, 'author') else context.user
            emb.add_field(name="Модератор：", value=author.mention, inline=True)

            await self.log_action(
                title="Разбан",
                fields=[
                    ("Пользователь", f"{user.mention} | **{user.name}**", True),
                    ("Модератор", author.mention, True)
                ],
                color=0x00FF00
            )

            # Удаляем из темпбанов, если был
            tempban_path = Path(__file__).parent.parent / "data" / "tempbans.json"
            if tempban_path.exists():
                try:
                    with open(tempban_path, "r", encoding="utf-8") as f:
                        tempbans = json.load(f)
                    if user_id in tempbans:
                        tempbans.pop(user_id)
                        with open(tempban_path, "w", encoding="utf-8") as f:
                            json.dump(tempbans, f, indent=2, ensure_ascii=False)
                except:
                    pass

            if isinstance(context, Interaction):
                await context.response.send_message(embed=emb)
            else:
                await context.send(embed=emb)

        except ValueError:
            await self._send_error(context, "❌ Неверный формат ID пользователя")
        except nextcord.NotFound:
            await self._send_error(context, "❌ Пользователь не найден или не в бан-листе")
        except Exception as e:
            await self._send_error(context, f"❌ Ошибка при разбане: {str(e)}")

    @nextcord.slash_command(name="mute", description="Выдать мут пользователю (timeout)")
    @commands.has_permissions(moderate_members=True)
    async def mute_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Участник для мута", required=True),
        time: str = SlashOption(description="Время (7д, 1д 12ч, 30м)", required=True),
        reason: str = SlashOption(description="Причина мута", required=False, default="Не указана")
    ):
        error = self._check_target(interaction.user, member)
        if error:
            await self._send_error(interaction, error)
            return
        await self._mute_command(interaction, member, time, reason)

    @commands.command(name="mute", description="Выдать мут пользователю на сервере (timeout)")
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx, member: nextcord.Member, time: str, *, reason: str = "Не указана"):
        error = self._check_target(ctx.author, member)
        if error:
            await self._send_error(ctx, error)
            return
        await self._mute_command(ctx, member, time, reason)

    async def _mute_command(self, context, member: nextcord.Member, time: str, reason: str):
        try:
            author = context.author if hasattr(context, 'author') else context.user
            time_seconds = self.parse_time(time)

            if time_seconds <= 0:
                await self._send_error(context, f"❌ Не удалось распознать время: `{time}`\nИспользуйте формат: `7д`, `1д 12ч`, `30м`")
                return

            timeout_end = nextcord.utils.utcnow() + datetime.timedelta(seconds=time_seconds)
            timestamp_formatted = int(timeout_end.timestamp())

            await member.edit(
                timeout=timeout_end,
                reason=f'{author.name}: {reason}'
            )

            emb = Embed(
                title="／ Выдача мута．",
                description="Пользователю был выдан мут на сервере．"
            )
            emb.add_field(name="Замьючен：", value=f"{member.mention} | **{member.name}**", inline=True)
            emb.add_field(name="Модератор：", value=f"{author.mention} | **{author.name}**", inline=True)
            emb.add_field(name="Длительность：", value=f"**{self.format_time(time_seconds)}**", inline=True)
            emb.add_field(name="Мут истекает：", value=f"<t:{timestamp_formatted}:R>", inline=True)
            emb.add_field(name="Причина：", value=f"**{reason}**", inline=False)

            await self.log_action(
                title="Выдача мута",
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Модератор", author.mention, True),
                    ("Длительность", self.format_time(time_seconds), True),
                    ("Причина", reason, False)
                ],
                color=0xFFA500
            )

            if isinstance(context, Interaction):
                await context.response.send_message(embed=emb)
            else:
                await context.send(embed=emb)

        except Exception as e:
            await self._send_error(context, f"❌ Ошибка при выдаче мута: {str(e)}")

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
        author = context.author if hasattr(context, 'author') else context.user
        await member.edit(timeout=None)

        emb = Embed(
            title="／ Снятие мута．",
            description="С пользователя был снят мут．"
        )
        emb.add_field(name="Размьючен：", value=f"{member.mention} | **{member.name}**", inline=True)
        emb.add_field(name="Модератор：", value=f"{author.mention} | **{author.name}**", inline=True)

        await self.log_action(
            title="Снятие мута",
            fields=[
                ("Пользователь", member.mention, True),
                ("Модератор", author.mention, True)
            ],
            color=0x00FF00
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
        error = self._check_target(interaction.user, member)
        if error:
            await self._send_error(interaction, error)
            return
        await self._kick_command(interaction, member, reason)

    @commands.command(name="kick", description="Выгнать пользователя с сервера")
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx, member: nextcord.Member, *, reason: str = "Не указана"):
        error = self._check_target(ctx.author, member)
        if error:
            await self._send_error(ctx, error)
            return
        await self._kick_command(ctx, member, reason)

    async def _kick_command(self, context, member: nextcord.Member, reason: str):
        author = context.author if hasattr(context, 'author') else context.user
        await member.kick(reason=f'{author.name}: {reason}')

        emb = Embed(
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
            ],
            color=0xFFA500
        )

        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)

def setup(bot):
    bot.add_cog(Moderation(bot))