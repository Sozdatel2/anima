import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui, Embed, ButtonStyle
from datetime import datetime, timedelta, timezone
import json
import asyncio
from pathlib import Path

class Curators(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CURATOR_CHANNEL_ID = 999337462583267378
        self.ANNOUNCE_CHANNEL_ID = 951923351729889400
        self.LOG_CHANNEL_ID = 1117078070239703071
        self.TRIAL_ROLE_ID = 884111133978533888
        self.VACATION_ROLE_ID = 1116734514702598154
        self.STAFF_ROLE_ID = 1090070131939475558

        self.MOD_ROLES = {
            "Head of Mod": 1505229944245059735,
            "Senior Moderator": 980836374557098034,
            "Moderator": 849779676922511370,
            "Trainee Moderator": 1001198066428289084
        }
        self.MOD_TEAM_ROLE = 1019691991707172874

        self.PR_ROLES = {
            "Head of PR": 1505229777303244914,
            "Senior PR Manager": 1508864686320521226,
            "PR Manager": 850599702050373694,
            "Trainee PR Manager": 1508864813327974594
        }
        self.PR_TEAM_ROLE = 1505230648346939452

        self.ADMIN_ROLE = 957679828176367647
        self.CURATOR_ROLE = 994284414584504372

        self.DATA_PATH = Path(__file__).parent.parent / "data" / "vocations.json"
        self.DATA_PATH.parent.mkdir(exist_ok=True)
        self.data = self.load_data()

    def load_data(self):
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_data(self):
        with open(self.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_user_history(self, user_id: str):
        return self.data.get(user_id, {"history": []})

    def add_history(self, user_id: str, entry: dict):
        if user_id not in self.data:
            self.data[user_id] = {"history": []}
        self.data[user_id]["history"].append(entry)
        self.save_data()

    def _get_managed_roles(self, author):
        author_roles = [r.id for r in author.roles]
        roles = {}

        if self.MOD_ROLES["Head of Mod"] in author_roles:
            roles.update(self.MOD_ROLES)
        if self.PR_ROLES["Head of PR"] in author_roles:
            roles.update(self.PR_ROLES)
        if 846338416303538226 in author_roles:
            roles.update(self.MOD_ROLES)
            roles.update(self.PR_ROLES)
            roles["Администратор"] = self.ADMIN_ROLE
            roles["Куратор"] = self.CURATOR_ROLE
        return roles

    def _can_manage(self, author, target_roles: list) -> bool:
        author_roles = [r.id for r in author.roles]
        if 846338416303538226 in author_roles:
            return True

        if self.MOD_ROLES["Head of Mod"] in author_roles:
            for role_id in target_roles:
                if role_id in self.MOD_ROLES.values():
                    continue
                if role_id == self.MOD_TEAM_ROLE:
                    continue
                return False
            return True

        if self.PR_ROLES["Head of PR"] in author_roles:
            for role_id in target_roles:
                if role_id in self.PR_ROLES.values():
                    continue
                if role_id == self.PR_TEAM_ROLE:
                    continue
                return False
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
        try:
            await channel.send(embed=embed)
        except:
            pass

    async def announce(self, title: str, description: str, color: int = 0x2B2D31, footer: str = None, icon_url: str = None):
        channel = self.bot.get_channel(self.ANNOUNCE_CHANNEL_ID)
        if not channel:
            return
        embed = Embed(
            title=f"／ {title}．",
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        if footer:
            embed.set_footer(text=footer, icon_url=icon_url)
        try:
            await channel.send(embed=embed)
        except:
            pass

    class AssignModal(ui.Modal):
        def __init__(self, cog, member, role_name, role_id):
            super().__init__(title=f"Назначение: {role_name}", timeout=300)
            self.cog = cog
            self.member = member
            self.role_name = role_name
            self.role_id = role_id

            self.probation_end = ui.TextInput(
                label="Дата окончания испытательного срока",
                placeholder="ДД.ММ.ГГГГ (или 'без' если нет)",
                min_length=1,
                max_length=12,
                required=True
            )
            self.add_item(self.probation_end)

        async def callback(self, interaction: Interaction):
            probation_end = self.probation_end.value.strip()
            if probation_end.lower() != "без":
                try:
                    datetime.strptime(probation_end, "%d.%m.%Y")
                except ValueError:
                    await interaction.response.send_message("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или 'без'", ephemeral=True)
                    return

            await interaction.response.send_message(f"✅ {self.member.mention} назначен на **{self.role_name}**", ephemeral=True)

            role = interaction.guild.get_role(self.role_id)
            if role:
                await self.member.add_roles(role)

            if self.role_id not in [self.cog.ADMIN_ROLE, self.cog.CURATOR_ROLE]:
                trial_role = interaction.guild.get_role(self.cog.TRIAL_ROLE_ID)
                if trial_role and probation_end.lower() != "без":
                    await self.member.add_roles(trial_role)

                staff_role = interaction.guild.get_role(self.cog.STAFF_ROLE_ID)
                if staff_role:
                    await self.member.add_roles(staff_role)

            entry = {
                "action": "назначен",
                "role": self.role_name,
                "date": datetime.now(timezone.utc).isoformat(),
                "probation_end": probation_end if probation_end.lower() != "без" else None,
                "moderator": interaction.user.display_name
            }
            self.cog.add_history(str(self.member.id), entry)

            try:
                embed_dm = Embed(
                    title="／ Назначение．",
                    description=f"Вы назначены на должность **{self.role_name}**",
                    color=0x00FF00
                )
                if probation_end.lower() != "без":
                    embed_dm.add_field(
                        name="Испытательный срок",
                        value=f"до **{probation_end}**",
                        inline=False
                    )
                embed_dm.add_field(name="Назначил", value=interaction.user.mention, inline=False)
                await self.member.send(embed=embed_dm)
            except:
                pass

            await self.cog.log_action(
                title="Назначение",
                fields=[
                    ("Сотрудник", self.member.mention, True),
                    ("Должность", self.role_name, True),
                    ("Испытательный срок", probation_end if probation_end.lower() != "без" else "Без срока", True),
                    ("Назначил", interaction.user.mention, True)
                ],
                color=0x00FF00
            )

            announce_text = f"{self.member.mention} назначен на должность **{self.role_name}**"
            if probation_end.lower() != "без":
                announce_text += f"\nИспытательный срок до **{probation_end}**"

            await self.cog.announce(
                title="Назначение",
                description=announce_text,
                color=0x00FF00,
                footer=f"Назначил: {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

    class PromoteModal(ui.Modal):
        def __init__(self, cog, member, new_role_name, new_role_id):
            super().__init__(title=f"Повышение: {new_role_name}", timeout=300)
            self.cog = cog
            self.member = member
            self.new_role_name = new_role_name
            self.new_role_id = new_role_id

            self.reason = ui.TextInput(
                label="Причина повышения",
                placeholder="Укажите причину",
                min_length=3,
                max_length=200,
                required=True
            )
            self.add_item(self.reason)

        async def callback(self, interaction: Interaction):
            await interaction.response.send_message(f"✅ {self.member.mention} повышен до **{self.new_role_name}**", ephemeral=True)

            mod_roles = list(self.cog.MOD_ROLES.values()) + [self.cog.MOD_TEAM_ROLE]
            pr_roles = list(self.cog.PR_ROLES.values()) + [self.cog.PR_TEAM_ROLE]
            all_staff_roles = mod_roles + pr_roles + [
                self.cog.TRIAL_ROLE_ID,
                self.cog.VACATION_ROLE_ID
            ]

            for role_id in all_staff_roles:
                role = interaction.guild.get_role(role_id)
                if role and role in self.member.roles:
                    await self.member.remove_roles(role)

            new_role = interaction.guild.get_role(self.new_role_id)
            if new_role:
                await self.member.add_roles(new_role)

            if self.new_role_id not in [self.cog.ADMIN_ROLE, self.cog.CURATOR_ROLE]:
                staff_role = interaction.guild.get_role(self.cog.STAFF_ROLE_ID)
                if staff_role and staff_role not in self.member.roles:
                    await self.member.add_roles(staff_role)

            entry = {
                "action": "повышен",
                "role": self.new_role_name,
                "date": datetime.now(timezone.utc).isoformat(),
                "reason": self.reason.value,
                "moderator": interaction.user.display_name
            }
            self.cog.add_history(str(self.member.id), entry)

            try:
                embed_dm = Embed(
                    title="／ Повышение．",
                    description=f"Вы повышены до **{self.new_role_name}**",
                    color=0x00FF00
                )
                embed_dm.add_field(name="Причина", value=self.reason.value, inline=False)
                embed_dm.add_field(name="Повысил", value=interaction.user.mention, inline=False)
                await self.member.send(embed=embed_dm)
            except:
                pass

            await self.cog.log_action(
                title="Повышение",
                fields=[
                    ("Сотрудник", self.member.mention, True),
                    ("Новая должность", self.new_role_name, True),
                    ("Причина", self.reason.value, False),
                    ("Повысил", interaction.user.mention, True)
                ],
                color=0x00FF00
            )

            await self.cog.announce(
                title="Повышение",
                description=f"{self.member.mention} повышен до **{self.new_role_name}**",
                color=0x00FF00,
                footer=f"Повысил: {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

    class VacationModal(ui.Modal):
        def __init__(self, cog, member):
            super().__init__(title="Отпуск", timeout=300)
            self.cog = cog
            self.member = member

            self.days = ui.TextInput(
                label="Количество дней",
                placeholder="Введите число (например: 14)",
                min_length=1,
                max_length=3,
                required=True
            )
            self.add_item(self.days)

        async def callback(self, interaction: Interaction):
            try:
                days = int(self.days.value)
                if days < 1 or days > 365:
                    raise ValueError
            except ValueError:
                await interaction.response.send_message("❌ Введите число от 1 до 365", ephemeral=True)
                return

            await interaction.response.send_message(f"✅ {self.member.mention} отправлен в отпуск на **{days}** дней", ephemeral=True)

            vacation_role = interaction.guild.get_role(self.cog.VACATION_ROLE_ID)
            if vacation_role:
                await self.member.add_roles(vacation_role)

            entry = {
                "action": "отпуск",
                "date_start": datetime.now(timezone.utc).isoformat(),
                "days": days,
                "moderator": interaction.user.display_name
            }
            self.cog.add_history(str(self.member.id), entry)

            try:
                embed_dm = Embed(
                    title="／ Отпуск．",
                    description=f"Вы отправлены в отпуск на **{days}** дней",
                    color=0xFFA500
                )
                embed_dm.add_field(name="Отправил", value=interaction.user.mention, inline=False)
                await self.member.send(embed=embed_dm)
            except:
                pass

            await self.cog.log_action(
                title="Отпуск",
                fields=[
                    ("Сотрудник", self.member.mention, True),
                    ("Дней", str(days), True),
                    ("Отправил", interaction.user.mention, True)
                ],
                color=0xFFA500
            )

            await self.cog.announce(
                title="Отпуск",
                description=f"{self.member.mention} уходит в отпуск на **{days}** дней",
                color=0xFFA500,
                footer=f"Отправил: {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

    class FireModal(ui.Modal):
        def __init__(self, cog, member):
            super().__init__(title="Увольнение", timeout=300)
            self.cog = cog
            self.member = member

            self.reason = ui.TextInput(
                label="Причина увольнения",
                placeholder="Укажите причину",
                min_length=3,
                max_length=200,
                required=True
            )
            self.add_item(self.reason)

        async def callback(self, interaction: Interaction):
            await interaction.response.send_message(f"✅ {self.member.mention} уволен.", ephemeral=True)

            mod_roles = list(self.cog.MOD_ROLES.values()) + [self.cog.MOD_TEAM_ROLE]
            pr_roles = list(self.cog.PR_ROLES.values()) + [self.cog.PR_TEAM_ROLE]
            all_staff_roles = mod_roles + pr_roles + [
                self.cog.TRIAL_ROLE_ID,
                self.cog.VACATION_ROLE_ID,
                self.cog.STAFF_ROLE_ID
            ]

            for role_id in all_staff_roles:
                role = interaction.guild.get_role(role_id)
                if role and role in self.member.roles:
                    await self.member.remove_roles(role)

            entry = {
                "action": "уволен",
                "date": datetime.now(timezone.utc).isoformat(),
                "reason": self.reason.value,
                "moderator": interaction.user.display_name
            }
            self.cog.add_history(str(self.member.id), entry)

            try:
                embed_dm = Embed(
                    title="／ Увольнение．",
                    description=f"Вы уволены с должности",
                    color=0xFF0000
                )
                embed_dm.add_field(name="Причина", value=self.reason.value, inline=False)
                embed_dm.add_field(name="Уволил", value=interaction.user.mention, inline=False)
                await self.member.send(embed=embed_dm)
            except:
                pass

            await self.cog.log_action(
                title="Увольнение",
                fields=[
                    ("Сотрудник", self.member.mention, True),
                    ("Причина", self.reason.value, False),
                    ("Уволил", interaction.user.mention, True)
                ],
                color=0xFF0000
            )

            await self.cog.announce(
                title="Увольнение",
                description=f"{self.member.mention} уволен. Причина: {self.reason.value}",
                color=0xFF0000,
                footer=f"Уволил: {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

    class ActionSelect(ui.View):
        def __init__(self, cog, member):
            super().__init__(timeout=120)
            self.cog = cog
            self.member = member

            options = [
                nextcord.SelectOption(label="Назначить", value="assign", emoji="📋"),
                nextcord.SelectOption(label="Повысить", value="promote", emoji="⬆️"),
                nextcord.SelectOption(label="Отпуск", value="vacation", emoji="🌴"),
                nextcord.SelectOption(label="Уволить", value="fire", emoji="🚫")
            ]

            self.select = nextcord.ui.Select(
                placeholder="Выберите действие",
                options=options,
                custom_id="action_select"
            )
            self.select.callback = self.select_callback
            self.add_item(self.select)

        async def select_callback(self, interaction: Interaction):
            action = self.select.values[0]
            author_roles = [r.id for r in interaction.user.roles]

            can_manage = False
            if 846338416303538226 in author_roles:
                can_manage = True
            if self.cog.MOD_ROLES["Head of Mod"] in author_roles:
                can_manage = True
            if self.cog.PR_ROLES["Head of PR"] in author_roles:
                can_manage = True

            if not can_manage:
                await interaction.response.send_message("❌ У вас нет прав на управление персоналом.", ephemeral=True)
                return

            if action == "assign":
                view = self.cog.RoleSelectView(self.cog, self.member)
                await interaction.response.send_message("Выберите должность:", view=view, ephemeral=True)
            elif action == "promote":
                view = self.cog.PromoteSelectView(self.cog, self.member)
                await interaction.response.send_message("Выберите новую должность:", view=view, ephemeral=True)
            elif action == "vacation":
                modal = self.cog.VacationModal(self.cog, self.member)
                await interaction.response.send_modal(modal)
            elif action == "fire":
                modal = self.cog.FireModal(self.cog, self.member)
                await interaction.response.send_modal(modal)

    class RoleSelectView(ui.View):
        def __init__(self, cog, member):
            super().__init__(timeout=120)
            self.cog = cog
            self.member = member

            options = []
            for name, role_id in cog.MOD_ROLES.items():
                options.append(nextcord.SelectOption(label=name, value=str(role_id)))
            for name, role_id in cog.PR_ROLES.items():
                options.append(nextcord.SelectOption(label=name, value=str(role_id)))

            options.append(nextcord.SelectOption(label="Администратор", value=str(cog.ADMIN_ROLE)))
            options.append(nextcord.SelectOption(label="Куратор", value=str(cog.CURATOR_ROLE)))

            self.select = nextcord.ui.Select(
                placeholder="Выберите должность",
                options=options,
                custom_id="role_select"
            )
            self.select.callback = self.select_callback
            self.add_item(self.select)

        async def select_callback(self, interaction: Interaction):
            role_id = int(self.select.values[0])
            role_name = None
            for name, rid in self.cog.MOD_ROLES.items():
                if rid == role_id:
                    role_name = name
                    break
            for name, rid in self.cog.PR_ROLES.items():
                if rid == role_id:
                    role_name = name
                    break
            if role_id == self.cog.ADMIN_ROLE:
                role_name = "Администратор"
            elif role_id == self.cog.CURATOR_ROLE:
                role_name = "Куратор"

            if not role_name:
                await interaction.response.send_message("❌ Ошибка: должность не найдена.", ephemeral=True)
                return

            modal = self.cog.AssignModal(self.cog, self.member, role_name, role_id)
            await interaction.response.send_modal(modal)

    class PromoteSelectView(ui.View):
        def __init__(self, cog, member):
            super().__init__(timeout=120)
            self.cog = cog
            self.member = member

            options = []
            for name, role_id in cog.MOD_ROLES.items():
                if name != "Head of Mod":
                    options.append(nextcord.SelectOption(label=name, value=str(role_id)))
            for name, role_id in cog.PR_ROLES.items():
                if name != "Head of PR":
                    options.append(nextcord.SelectOption(label=name, value=str(role_id)))

            options.append(nextcord.SelectOption(label="Администратор", value=str(cog.ADMIN_ROLE)))
            options.append(nextcord.SelectOption(label="Куратор", value=str(cog.CURATOR_ROLE)))

            self.select = nextcord.ui.Select(
                placeholder="Выберите новую должность",
                options=options,
                custom_id="promote_select"
            )
            self.select.callback = self.select_callback
            self.add_item(self.select)

        async def select_callback(self, interaction: Interaction):
            role_id = int(self.select.values[0])
            role_name = None
            for name, rid in self.cog.MOD_ROLES.items():
                if rid == role_id:
                    role_name = name
                    break
            for name, rid in self.cog.PR_ROLES.items():
                if rid == role_id:
                    role_name = name
                    break
            if role_id == self.cog.ADMIN_ROLE:
                role_name = "Администратор"
            elif role_id == self.cog.CURATOR_ROLE:
                role_name = "Куратор"

            if not role_name:
                await interaction.response.send_message("❌ Ошибка: должность не найдена.", ephemeral=True)
                return

            modal = self.cog.PromoteModal(self.cog, self.member, role_name, role_id)
            await interaction.response.send_modal(modal)

    @commands.command(name="set-vocation", aliases=["staff", "куратор"])
    async def set_vocation(self, ctx, member: nextcord.Member):
        if ctx.channel.id != self.CURATOR_CHANNEL_ID:
            await ctx.send("❌ Команда доступна только в канале кураторов.", delete_after=10)
            return

        author_roles = [r.id for r in ctx.author.roles]
        can_manage = False

        # Проверка: овнер, хеды, куратор
        if 846338416303538226 in author_roles:           # Овнер
            can_manage = True
        elif self.MOD_ROLES["Head of Mod"] in author_roles:  # Хед модерации
            can_manage = True
        elif self.PR_ROLES["Head of PR"] in author_roles:    # Хед PR
            can_manage = True
        elif self.CURATOR_ROLE in author_roles:              # Куратор (994284414584504372)
            can_manage = True

        if not can_manage:
            await ctx.send("❌ У вас нет прав на управление персоналом.", delete_after=10)
            return

        embed = Embed(
            title="／ Управление сотрудником．",
            description=f"Выберите действие для {member.mention}",
            color=0x2B2D31,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Выберите действие в меню ниже")

        view = self.ActionSelect(self, member)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="vocation")
    async def vocation(self, ctx, member: nextcord.Member):
        author_roles = [r.id for r in ctx.author.roles]

        can_view = False
        if 846338416303538226 in author_roles:           # Овнер
            can_view = True
        elif self.MOD_ROLES["Head of Mod"] in author_roles:  # Хед модерации
            can_view = True
        elif self.PR_ROLES["Head of PR"] in author_roles:    # Хед PR
            can_view = True
        elif self.CURATOR_ROLE in author_roles:              # Куратор
            can_view = True

        if not can_view:
            await ctx.send("❌ У вас нет прав на просмотр истории сотрудников.", delete_after=10)
            return

        data = self.get_user_history(str(member.id))
        history = data.get("history", [])

        if not history:
            await ctx.send(f"❌ У {member.mention} нет истории.")
            return

        embed = Embed(
            title=f"／ История {member.display_name}．",
            color=0x2B2D31,
            timestamp=datetime.now(timezone.utc)
        )

        for entry in history[-10:]:
            action = entry.get("action", "неизвестно")
            date = entry.get("date", "").split("T")[0]
            role = entry.get("role", "")
            text = f"**{action}**"
            if role:
                text += f" → {role}"
            if "reason" in entry:
                text += f"\nПричина: {entry['reason']}"
            if "probation_end" in entry and entry["probation_end"]:
                text += f"\nИсп. срок до: {entry['probation_end']}"
            embed.add_field(name=f"📅 {date}", value=text, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="my_vocation")
    async def my_vocation(self, ctx):
        data = self.get_user_history(str(ctx.author.id))
        history = data.get("history", [])

        if not history:
            await ctx.send("❌ У вас нет истории.")
            return

        embed = Embed(
            title=f"／ Моя история．",
            color=0x2B2D31,
            timestamp=datetime.now(timezone.utc)
        )

        for entry in history[-10:]:
            action = entry.get("action", "неизвестно")
            date = entry.get("date", "").split("T")[0]
            role = entry.get("role", "")
            text = f"**{action}**"
            if role:
                text += f" → {role}"
            if "reason" in entry:
                text += f"\nПричина: {entry['reason']}"
            if "probation_end" in entry and entry["probation_end"]:
                text += f"\nИсп. срок до: {entry['probation_end']}"
            embed.add_field(name=f"📅 {date}", value=text, inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Curators(bot))