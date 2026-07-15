## Импорты библиотек
import nextcord
import datetime
import humanfriendly

## Импорты из файлов/библиотек
from nextcord.ext import commands
from nextcord import Interaction, SlashOption

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
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
        """Основной метод для выдачи мута"""
        try:
            time_seconds = humanfriendly.parse_timespan(time)
            timeout_end = nextcord.utils.utcnow() + datetime.timedelta(seconds=time_seconds)
            timestamp_formatted = int(timeout_end.timestamp())

            await member.edit(
                timeout=timeout_end,
                reason=f'{context.author.name} | {reason}'
            )
            
            emb = nextcord.Embed(
                title="／ Выдача мута．",
                description="Пользователю был выдан мут на сервере．"
            )
            emb.add_field(name="Замьючен：", value=f"{member.mention} | **{member.name}**", inline=True)
            emb.add_field(name="Модератор：", value=f"{context.author.mention} | **{context.author.name}**", inline=True)
            emb.add_field(name="Мут истекает：", value=f"<t:{timestamp_formatted}:R>", inline=True)
            emb.add_field(name="Причина：", value=f"**{reason}**", inline=False)

            if isinstance(context, Interaction):
                await context.response.send_message(embed=emb)
            else:
                await context.send(embed=emb)
                
        except humanfriendly.InvalidTimespan:
            error_emb = nextcord.Embed(
                description="❌ Некорректный формат времени．Используйте： `10s`, `5m`, `1h`, `1d`",
                color=0xE10000
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
        """Основной метод для снятия мута"""
        await member.edit(timeout=None)

        emb = nextcord.Embed(
            title="／ Снятие мута．",
            description="С пользователя был снят мут．"
        )
        emb.add_field(name="Размьючен：", value=f"{member.mention} | **{member.name}**", inline=True)
        emb.add_field(name="Модератор：", value=f"{context.author.mention} | **{context.author.name}**", inline=True)

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
        """Основной метод для кика"""
        author = context.author
        await member.kick(reason=f'{author.name}: {reason}')

        emb = nextcord.Embed(
            title="／ Участник кикнут．",
            description="Пользователь был успешно кикнут с сервера．"
        )
        emb.add_field(name="Кикнут：", value=f"{member.mention} | **{member.name}**", inline=True)
        emb.add_field(name="Модератор：", value=f"{author.mention} | **{author.name}**", inline=True)
        emb.add_field(name="Причина：", value=f"**{reason}**", inline=False)

        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)

def setup(bot):
    bot.add_cog(Moderation(bot))