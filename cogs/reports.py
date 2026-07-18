import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui, Embed, ButtonStyle
from datetime import datetime, timezone

class Reports(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.REPORT_CHANNEL_ID = 847047559675510784  # ← НОВЫЙ КАНАЛ ДЛЯ РЕПОРТОВ (МОДЕРАТОРЫ)
        self.LOG_CHANNEL_ID = 1234596840008323162     # Лог-канал для админов
        self.MOD_ROLE_ID = 1019691991707172874
        self.MOD_ROLES_ALLOWED = [
            1019691991707172874,  # Модератор
            1505229944245059735,  # Хед модерации
            994284414584504372,   # Куратор
            957679828176367647,   # Администратор
            846338416303538226    # Овнеры
        ]

    async def log_action(self, title: str, fields: list = None, color: int = 0x2B2D31):
        """Логирование для админов (в лог-канал)"""
        channel = self.bot.get_channel(self.LOG_CHANNEL_ID)
        if not channel:
            return
        embed = Embed(
            title=f"／ {title}．",
            timestamp=datetime.now(timezone.utc),
            color=color
        )
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        await channel.send(embed=embed)

    class ReportView(ui.View):
        def __init__(self, report_id: int, reporter_id: int, reported_id: int, reason: str, cog):
            super().__init__(timeout=None)
            self.report_id = report_id
            self.reporter_id = reporter_id
            self.reported_id = reported_id
            self.reason = reason
            self.cog = cog

        @ui.button(label="Принять", style=ButtonStyle.success, emoji="✅")
        async def accept_button(self, button: Interaction, _):
            if not any(role.id in self.cog.MOD_ROLES_ALLOWED for role in button.user.roles):
                await button.response.send_message("❌ У вас нет прав!", ephemeral=True)
                return

            await button.message.edit(view=None)
            embed = button.message.embeds[0]
            embed.color = 0x00FF00
            embed.add_field(name="Статус", value=f"✅ **Принят** модератором {button.user.mention}", inline=False)
            await button.message.edit(embed=embed)

            try:
                reporter = await self.cog.bot.fetch_user(self.reporter_id)
                embed_user = Embed(
                    title="／ Ваш репорт принят．",
                    description=f"Ваша жалоба на <@{self.reported_id}> была **принята** модерацией",
                    color=0x00FF00
                )
                embed_user.add_field(name="Причина", value=f"**{self.reason}**", inline=False)
                embed_user.add_field(name="Модератор", value=button.user.mention, inline=True)
                await reporter.send(embed=embed_user)
            except:
                pass

            await self.cog.log_action(
                title="Репорт принят",
                fields=[
                    ("Репорт #", f"**{self.report_id}**", True),
                    ("Модератор", button.user.mention, True),
                    ("Пользователь", f"<@{self.reported_id}>", True),
                    ("Причина", self.reason, False)
                ],
                color=0x00FF00
            )

            await button.response.send_message("✅ Репорт принят!", ephemeral=True)

        @ui.button(label="Отклонить", style=ButtonStyle.danger, emoji="❌")
        async def reject_button(self, button: Interaction, _):
            if not any(role.id in self.cog.MOD_ROLES_ALLOWED for role in button.user.roles):
                await button.response.send_message("❌ У вас нет прав!", ephemeral=True)
                return

            await button.message.edit(view=None)
            embed = button.message.embeds[0]
            embed.color = 0xFF0000
            embed.add_field(name="Статус", value=f"❌ **Отклонён** модератором {button.user.mention}", inline=False)
            await button.message.edit(embed=embed)

            try:
                reporter = await self.cog.bot.fetch_user(self.reporter_id)
                embed_user = Embed(
                    title="／ Ваш репорт отклонён．",
                    description=f"Ваша жалоба на <@{self.reported_id}> была **отклонена**",
                    color=0xFF0000
                )
                embed_user.add_field(name="Причина", value=f"**{self.reason}**", inline=False)
                embed_user.add_field(name="Модератор", value=button.user.mention, inline=True)
                await reporter.send(embed=embed_user)
            except:
                pass

            await self.cog.log_action(
                title="Репорт отклонён",
                fields=[
                    ("Репорт #", f"**{self.report_id}**", True),
                    ("Модератор", button.user.mention, True),
                ],
                color=0xFF0000
            )

            await button.response.send_message("❌ Репорт отклонён!", ephemeral=True)

    @commands.command(name="report", description="Пожаловаться на пользователя")
    async def report(self, ctx, member: nextcord.Member, *, reason: str = "Не указана"):
        if member.id == ctx.author.id:
            await ctx.send("❌ Нельзя пожаловаться на самого себя!")
            return
        if member.guild_permissions.administrator:
            await ctx.send("❌ Нельзя пожаловаться на администратора!")
            return

        report_id = len(self.bot.cogs) * 1000 + ctx.message.id % 1000
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel:
            await ctx.send("❌ Канал для репортов не найден!")
            return

        embed = Embed(
            title="／ Новый репорт．",
            description=f"Пользователь **{ctx.author.name}** подал жалобу",
            color=0xFFA500,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="ID репорта", value=f"`#{report_id}`", inline=True)
        embed.add_field(name="Нарушитель", value=member.mention, inline=True)
        embed.add_field(name="Автор репорта", value=ctx.author.mention, inline=True)
        embed.add_field(name="Причина", value=f"**{reason}**", inline=False)

        view = self.ReportView(report_id, ctx.author.id, member.id, reason, self)
        await channel.send(content=f"<@&{self.MOD_ROLE_ID}>", embed=embed, view=view)

        try:
            embed_user = Embed(
                title="／ Репорт отправлен．",
                description=f"Ваша жалоба на **{member.name}** была отправлена",
                color=0x00FF00
            )
            embed_user.add_field(name="Причина", value=f"**{reason}**", inline=False)
            embed_user.add_field(name="ID репорта", value=f"`#{report_id}`", inline=True)
            await ctx.author.send(embed=embed_user)
        except:
            pass

        await ctx.send(f"✅ Репорт отправлен! ID: `#{report_id}`")

        await self.log_action(
            title="Новый репорт",
            fields=[
                ("ID", f"`#{report_id}`", True),
                ("Автор", ctx.author.mention, True),
                ("Нарушитель", member.mention, True),
                ("Причина", reason, False)
            ],
            color=0xFFA500
        )

    @nextcord.slash_command(name="report", description="Пожаловаться на пользователя")
    async def report_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Нарушитель", required=True),
        reason: str = SlashOption(description="Причина жалобы", required=False, default="Не указана")
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ Нельзя пожаловаться на самого себя!", ephemeral=True)
            return
        if member.guild_permissions.administrator:
            await interaction.response.send_message("❌ Нельзя пожаловаться на администратора!", ephemeral=True)
            return

        report_id = len(self.bot.cogs) * 1000 + interaction.id % 1000
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Канал для репортов не найден!", ephemeral=True)
            return

        embed = Embed(
            title="／ Новый репорт．",
            description=f"Пользователь **{interaction.user.name}** подал жалобу",
            color=0xFFA500,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="ID репорта", value=f"`#{report_id}`", inline=True)
        embed.add_field(name="Нарушитель", value=member.mention, inline=True)
        embed.add_field(name="Автор репорта", value=interaction.user.mention, inline=True)
        embed.add_field(name="Причина", value=f"**{reason}**", inline=False)

        view = self.ReportView(report_id, interaction.user.id, member.id, reason, self)
        await channel.send(content=f"<@&{self.MOD_ROLE_ID}>", embed=embed, view=view)

        try:
            embed_user = Embed(
                title="／ Репорт отправлен．",
                description=f"Ваша жалоба на **{member.name}** была отправлена",
                color=0x00FF00
            )
            embed_user.add_field(name="Причина", value=f"**{reason}**", inline=False)
            embed_user.add_field(name="ID репорта", value=f"`#{report_id}`", inline=True)
            await interaction.user.send(embed=embed_user)
        except:
            pass

        await interaction.response.send_message(f"✅ Репорт отправлен! ID: `#{report_id}`")

        await self.log_action(
            title="Новый репорт",
            fields=[
                ("ID", f"`#{report_id}`", True),
                ("Автор", interaction.user.mention, True),
                ("Нарушитель", member.mention, True),
                ("Причина", reason, False)
            ],
            color=0xFFA500
        )

def setup(bot):
    bot.add_cog(Reports(bot))