import nextcord
import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui, Embed, ButtonStyle

class Nokta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DATA_PATH = Path(__file__).parent.parent / "data" / "nokta.json"
        self.LOG_CHANNEL_ID = 1234596840008323162
        self.MOD_ROLES = [
            1505229944245059735,
            994284414584504372,
            957679828176367647,
            846338416303538226
        ]
        self.DATA_PATH.parent.mkdir(exist_ok=True)
        self.data = self.load_data()
        self.bot.loop.create_task(self.check_noktas())

    def load_data(self):
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_data(self):
        with open(self.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_warns(self, user_id: int):
        return self.data.get(str(user_id), [])

    def get_active_warns(self, user_id: int):
        now = datetime.now(timezone.utc)
        warns = self.get_warns(user_id)
        active = []
        for w in warns:
            if w.get("permanent", False):
                active.append(w)
            elif w.get("expires_at"):
                exp = datetime.fromisoformat(w["expires_at"])
                if exp > now:
                    active.append(w)
        return active

    def add_warn(self, user_id: int, moderator_id: int, reason: str, days: int = 30):
        if str(user_id) not in self.data:
            self.data[str(user_id)] = []
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=days)
        self.data[str(user_id)].append({
            "reason": reason,
            "moderator_id": moderator_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "permanent": days == 0
        })
        self.save_data()

    def clear_warns(self, user_id: int):
        if str(user_id) in self.data:
            self.data[str(user_id)] = []
            self.save_data()
            return True
        return False

    async def log_action(self, title: str, fields: list = None, color: int = 0x2B2D31):
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

    class ExtendModal(ui.Modal):
        def __init__(self, user_id: int, warn_index: int, cog):
            super().__init__(title="Продление нокты", timeout=120)
            self.user_id = user_id
            self.warn_index = warn_index
            self.cog = cog

            self.days = ui.TextInput(
                label="Количество дней (0 = перманентно)",
                placeholder="Введите число от 0 до 365",
                min_length=1,
                max_length=3,
                required=True
            )
            self.add_item(self.days)

        async def callback(self, interaction: Interaction):
            try:
                days = int(self.days.value)
                if days < 0 or days > 365:
                    raise ValueError("Должно быть от 0 до 365")
            except ValueError:
                await interaction.response.send_message("❌ Введите число от 0 до 365!", ephemeral=True)
                return

            user_id_str = str(self.user_id)
            if user_id_str not in self.cog.data:
                await interaction.response.send_message("❌ Нокта не найдена!", ephemeral=True)
                return

            warns = self.cog.data[user_id_str]
            if self.warn_index >= len(warns):
                await interaction.response.send_message("❌ Нокта не найдена!", ephemeral=True)
                return

            warn = warns[self.warn_index]
            if days == 0:
                warn["permanent"] = True
                warn["expires_at"] = None
                msg = "перманентная"
            else:
                now = datetime.now(timezone.utc)
                new_exp = now + timedelta(days=days)
                warn["expires_at"] = new_exp.isoformat()
                warn["permanent"] = False
                msg = f"продлена на **{days}** дней"

            self.cog.save_data()

            embed = Embed(
                title="／ Продление нокты．",
                description=f"Нокта пользователя <@{self.user_id}> **{msg}**",
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)

            await interaction.response.send_message(embed=embed)

            await self.cog.log_action(
                title="Продление нокты",
                fields=[
                    ("Пользователь", f"<@{self.user_id}>", True),
                    ("Модератор", interaction.user.mention, True),
                    ("Статус", msg, False)
                ]
            )

    class ExtendButton(ui.View):
        def __init__(self, user_id: int, warn_index: int, cog):
            super().__init__(timeout=None)
            self.user_id = user_id
            self.warn_index = warn_index
            self.cog = cog

        @ui.button(label="Продлить нокту", style=ButtonStyle.primary, emoji="📌")
        async def extend_button(self, button, interaction):
            has_role = any(role.id in self.cog.MOD_ROLES for role in interaction.user.roles)
            if not has_role:
                await interaction.response.send_message("❌ У вас нет прав для продления нокты!", ephemeral=True)
                return

            modal = self.cog.ExtendModal(self.user_id, self.warn_index, self.cog)
            await interaction.response.send_modal(modal)

    async def check_noktas(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now(timezone.utc)
            changed = False
            for user_id_str, user_data in list(self.data.items()):
                user_id = int(user_id_str)

                new_warns = []
                for w in user_data:
                    if w.get("permanent", False):
                        new_warns.append(w)
                    elif w.get("expires_at"):
                        exp = datetime.fromisoformat(w["expires_at"])
                        if exp > now:
                            new_warns.append(w)
                if len(new_warns) != len(user_data):
                    self.data[user_id_str] = new_warns
                    changed = True

                active = self.get_active_warns(user_id)
                warn_count = len(active)

                guild = self.bot.get_guild(798974707880689664)
                if not guild:
                    continue

                member = guild.get_member(user_id)
                if not member:
                    continue

                moderation = self.bot.get_cog("Moderation")
                if not moderation:
                    continue

                if warn_count >= 5:
                    await moderation._tempban_command(
                        context=None,
                        member=member,
                        time="30d",
                        reason="Достигнут лимит 5 нокт"
                    )
                    self.data[user_id_str] = []
                    changed = True
                    await self.log_action(
                        title="Автоматический бан",
                        fields=[
                            ("Пользователь", member.mention, True),
                            ("Причина", "Достигнут лимит 5 нокт", False)
                        ],
                        
                    )
                    continue

                if warn_count >= 3:
                    await moderation._mute_command(
                        context=None,
                        member=member,
                        time="2d",
                        reason="Достигнут лимит 3 нокт"
                    )
                    await self.log_action(
                        title="Автоматический мут",
                        fields=[
                            ("Пользователь", member.mention, True),
                            ("Причина", "Достигнут лимит 3 нокт", False)
                        ]
                    )
                    continue

            if changed:
                self.save_data()

            await asyncio.sleep(3600)

    # ==========================================
    # 🔹 ПРЕФИКСНЫЕ КОМАНДЫ
    # ==========================================

    @commands.command(name="nokta", description="Выдать нокту (варн) пользователю")
    @commands.has_permissions(moderate_members=True)
    async def nokta(self, ctx, member: nextcord.Member, *, reason: str = "Не указана"):
        if member.id == ctx.author.id:
            await ctx.send("❌ Нельзя выдать нокту самому себе!")
            return

        if member.guild_permissions.administrator:
            await ctx.send("❌ Нельзя выдать нокту администратору!")
            return

        self.add_warn(member.id, ctx.author.id, reason, 30)
        active = self.get_active_warns(member.id)
        warn_count = len(active)

        embed = Embed(
            title="／ Выдача нокты．",
            description=f"Пользователь **{member.name}** получил нокту",
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Причина", value=f"**{reason}**", inline=False)
        embed.add_field(name="Всего нокт", value=f"**{warn_count}**", inline=True)
        embed.add_field(name="Модератор", value=ctx.author.mention, inline=True)

        user_warns = self.data.get(str(member.id), [])
        warn_index = len(user_warns) - 1

        view = self.ExtendButton(member.id, warn_index, self)
        await ctx.send(embed=embed, view=view)

        await self.log_action(
            title="Выдача нокты",
            fields=[
                ("Пользователь", member.mention, True),
                ("Модератор", ctx.author.mention, True),
                ("Причина", reason, False),
                ("Всего нокт", str(warn_count), True)
            ]
        )

    @commands.command(name="my_nokta", description="Посмотреть свои активные нокты")
    async def my_nokta(self, ctx):
        active = self.get_active_warns(ctx.author.id)

        if not active:
            embed = Embed(
                title="／ Мои нокты．",
                description="✅ У вас нет активных нокт"
            )
            await ctx.send(embed=embed)
            return

        embed = Embed(
            title="／ Мои нокты．",
            description=f"У вас **{len(active)}** активных нокт"
        )
        for i, w in enumerate(active[:5], 1):
            mod = self.bot.get_user(w["moderator_id"])
            mod_name = mod.name if mod else "Unknown"
            expires = "🔒 Перманентная" if w.get("permanent") else f"⌛ Истекает： <t:{int(datetime.fromisoformat(w['expires_at']).timestamp())}:R>"
            embed.add_field(
                name=f"Нокта #{i}",
                value=f"Причина： {w['reason']}\nМодератор： {mod_name}\nСтатус： {expires}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="nokta_list", description="Показать нокты пользователя (только для модерации)")
    @commands.has_permissions(moderate_members=True)
    async def nokta_list(self, ctx, member: nextcord.Member):
        active = self.get_active_warns(member.id)

        embed = Embed(
            title=f"／ Нокты пользователя {member.name}．",
            description=f"Всего активных нокт： **{len(active)}**",
            color=0x2B2D31
        )

        if not active:
            embed.description += "\n\n✅ У пользователя нет активных нокт"
        else:
            for i, w in enumerate(active[:10], 1):
                mod = self.bot.get_user(w["moderator_id"])
                mod_name = mod.name if mod else "Unknown"
                expires = "🔒 Перманентная" if w.get("permanent") else f"⌛ Истекает： <t:{int(datetime.fromisoformat(w['expires_at']).timestamp())}:R>"
                embed.add_field(
                    name=f"Нокта #{i}",
                    value=f"Причина： {w['reason']}\nМодератор： {mod_name}\nСтатус： {expires}",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.command(name="clear_nokta", description="Очистить все нокты пользователя (только для админов)")
    @commands.has_permissions(administrator=True)
    async def clear_nokta(self, ctx, member: nextcord.Member):
        if self.clear_warns(member.id):
            embed = Embed(
                title="／ Очистка нокт．",
                description=f"✅ Все нокты пользователя **{member.name}** очищены",
                
            )
            await ctx.send(embed=embed)

            await self.log_action(
                title="Очистка нокт",
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Модератор", ctx.author.mention, True)
                ],
                
            )
        else:
            embed = Embed(
                title="／ Очистка нокт．",
                description=f"❌ У пользователя **{member.name}** нет нокт"
            )
            await ctx.send(embed=embed)

    # ==========================================
    # 🔹 СЛЕШ-КОМАНДЫ
    # ==========================================

    @nextcord.slash_command(name="nokta", description="Выдать нокту (варн) пользователю")
    @commands.has_permissions(moderate_members=True)
    async def nokta_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Участник для нокты", required=True),
        reason: str = SlashOption(description="Причина нокты", required=False, default="Не указана")
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ Нельзя выдать нокту самому себе!", ephemeral=True)
            return

        if member.guild_permissions.administrator:
            await interaction.response.send_message("❌ Нельзя выдать нокту администратору!", ephemeral=True)
            return

        self.add_warn(member.id, interaction.user.id, reason, 30)
        active = self.get_active_warns(member.id)
        warn_count = len(active)

        embed = Embed(
            title="／ Выдача нокты．",
            description=f"Пользователь **{member.name}** получил нокту",
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Причина", value=f"**{reason}**", inline=False)
        embed.add_field(name="Всего нокт", value=f"**{warn_count}**", inline=True)
        embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)

        user_warns = self.data.get(str(member.id), [])
        warn_index = len(user_warns) - 1

        view = self.ExtendButton(member.id, warn_index, self)
        await interaction.response.send_message(embed=embed, view=view)

        await self.log_action(
            title="Выдача нокты",
            fields=[
                ("Пользователь", member.mention, True),
                ("Модератор", interaction.user.mention, True),
                ("Причина", reason, False),
                ("Всего нокт", str(warn_count), True)
            ]
        )

    @nextcord.slash_command(name="my_nokta", description="Посмотреть свои активные нокты")
    async def my_nokta_slash(self, interaction: Interaction):
        active = self.get_active_warns(interaction.user.id)

        if not active:
            embed = Embed(
                title="／ Мои нокты．",
                description="✅ У вас нет активных нокт",
                
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = Embed(
            title="／ Мои нокты．",
            description=f"У вас **{len(active)}** активных нокт"
        )
        for i, w in enumerate(active[:5], 1):
            mod = self.bot.get_user(w["moderator_id"])
            mod_name = mod.name if mod else "Unknown"
            expires = "🔒 Перманентная" if w.get("permanent") else f"⌛ Истекает： <t:{int(datetime.fromisoformat(w['expires_at']).timestamp())}:R>"
            embed.add_field(
                name=f"Нокта #{i}",
                value=f"Причина： {w['reason']}\nМодератор： {mod_name}\nСтатус： {expires}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="nokta_list", description="Показать нокты пользователя (только для модерации)")
    @commands.has_permissions(moderate_members=True)
    async def nokta_list_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Пользователь для просмотра нокт", required=True)
    ):
        active = self.get_active_warns(member.id)

        embed = Embed(
            title=f"／ Нокты пользователя {member.name}．",
            description=f"Всего активных нокт： **{len(active)}**"
        )

        if not active:
            embed.description += "\n\n✅ У пользователя нет активных нокт"
        else:
            for i, w in enumerate(active[:10], 1):
                mod = self.bot.get_user(w["moderator_id"])
                mod_name = mod.name if mod else "Unknown"
                expires = "🔒 Перманентная" if w.get("permanent") else f"⌛ Истекает： <t:{int(datetime.fromisoformat(w['expires_at']).timestamp())}:R>"
                embed.add_field(
                    name=f"Нокта #{i}",
                    value=f"Причина： {w['reason']}\nМодератор： {mod_name}\nСтатус： {expires}",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @nextcord.slash_command(name="clear_nokta", description="Очистить все нокты пользователя (только для админов)")
    @commands.has_permissions(administrator=True)
    async def clear_nokta_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="Пользователь для очистки нокт", required=True)
    ):
        if self.clear_warns(member.id):
            embed = Embed(
                title="／ Очистка нокт．",
                description=f"✅ Все нокты пользователя **{member.name}** очищены"
            )
            await interaction.response.send_message(embed=embed)

            await self.log_action(
                title="Очистка нокт",
                fields=[
                    ("Пользователь", member.mention, True),
                    ("Модератор", interaction.user.mention, True)
                ]
            )
        else:
            embed = Embed(
                title="／ Очистка нокт．",
                description=f"❌ У пользователя **{member.name}** нет нокт"
            )
            await interaction.response.send_message(embed=embed)

def setup(bot):
    bot.add_cog(Nokta(bot))