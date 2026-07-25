import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui, Embed, ButtonStyle, PermissionOverwrite
from datetime import datetime, timezone
from nextcord.utils import escape_mentions
from pathlib import Path
import json
import secrets
import io
import logging

logger = logging.getLogger(__name__)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TICKET_CHANNEL_ID = 846329342983143434
        self.TICKET_CATEGORY_ID = 1044213985257459732
        self.MOD_ROLE_ID = 1019691991707172874
        self.MOD_ROLES_ALLOWED = [
            1019691991707172874,
            1505229944245059735,
            994284414584504372,
            957679828176367647,
            846338416303538226
        ]
        self.LOG_CHANNEL_ID = 1234596840008323162

        self.DATA_PATH = Path(__file__).parent.parent / "data" / "ticket_views.json"
        self.DATA_PATH.parent.mkdir(exist_ok=True)

        self.view_data = self.load_view_data()

        self.bot.add_view(self.CreateTicketView(self))
        self.bot.loop.create_task(self.cleanup_and_restore())

    def load_view_data(self):
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_view_data(self):
        with open(self.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.view_data, f, indent=2, ensure_ascii=False)

    async def cleanup_and_restore(self):
        await self.bot.wait_until_ready()

        to_delete = []
        for msg_id, data in self.view_data.items():
            channel = self.bot.get_channel(data["channel_id"])
            if not channel:
                to_delete.append(msg_id)
                continue

            try:
                msg = await channel.fetch_message(int(msg_id))
            except (nextcord.NotFound, nextcord.Forbidden, nextcord.HTTPException):
                to_delete.append(msg_id)
                continue

            view = self.TicketControlView(
                data["ticket_id"],
                data["author_id"],
                data["target_id"],
                channel,
                self
            )

            for item in view.children:
                if item.label == "Взять в работу" and data.get("taken", False):
                    item.disabled = True
                if item.label == "Удалить обращение" and data.get("closed", False):
                    item.disabled = True

            try:
                await msg.edit(view=view)
                self.bot.add_view(view, message_id=int(msg_id))
            except (nextcord.Forbidden, nextcord.HTTPException):
                to_delete.append(msg_id)

        for msg_id in to_delete:
            self.view_data.pop(msg_id, None)

        self.save_view_data()

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
        except (nextcord.Forbidden, nextcord.HTTPException) as e:
            logger.warning(f"Failed to send log: {e}")

    class TicketModal(ui.Modal):
        def __init__(self, cog):
            super().__init__(title="Создание тикета", timeout=300)
            self.cog = cog

            self.target = ui.TextInput(
                label="На кого жалоба? (ID или @упоминание)",
                placeholder="Введите ID пользователя или упомяните его",
                min_length=1,
                max_length=50,
                required=True
            )
            self.add_item(self.target)

            self.reason = ui.TextInput(
                label="Причина обращения",
                placeholder="Опишите суть проблемы",
                min_length=5,
                max_length=500,
                required=True
            )
            self.add_item(self.reason)

            self.evidence = ui.TextInput(
                label="Доказательства (ссылка или описание)",
                placeholder="Прикрепите ссылку на скриншот или опишите доказательства",
                min_length=1,
                max_length=500,
                required=False
            )
            self.add_item(self.evidence)

        async def callback(self, interaction: Interaction):
            target_input = self.target.value.strip()
            target_id = None

            if target_input.isdigit():
                target_id = int(target_input)
            elif "<@" in target_input and ">" in target_input:
                try:
                    target_id = int(target_input.replace("<@", "").replace(">", "").replace("!", ""))
                except:
                    pass

            if not target_id:
                await interaction.response.send_message(
                    "❌ Не удалось определить пользователя. Введите корректный ID или упоминание.",
                    ephemeral=True
                )
                return

            target_user = interaction.guild.get_member(target_id)
            if not target_user:
                await interaction.response.send_message("❌ Пользователь не найден на сервере.", ephemeral=True)
                return

            if target_user.id == interaction.user.id:
                await interaction.response.send_message("❌ Нельзя создать тикет на самого себя!", ephemeral=True)
                return

            for data in self.cog.view_data.values():
                if data.get("author_id") == interaction.user.id and not data.get("closed", False):
                    channel = self.cog.bot.get_channel(data["channel_id"])
                    if channel:
                        await interaction.response.send_message(
                            f"❌ У вас уже есть открытый тикет! Перейдите в {channel.mention}",
                            ephemeral=True
                        )
                        return
                    else:
                        data["closed"] = True
                        self.cog.save_view_data()

            category = interaction.guild.get_channel(self.cog.TICKET_CATEGORY_ID)
            if not category:
                await interaction.response.send_message("❌ Категория для тикетов не найдена! Сообщите администрации.", ephemeral=True)
                return

            ticket_id = secrets.randbelow(900000) + 100000
            existing_ids = [data["ticket_id"] for data in self.cog.view_data.values()]
            while ticket_id in existing_ids:
                ticket_id = secrets.randbelow(900000) + 100000

            channel_name = f"тикет-{ticket_id}"

            overwrites = {
                interaction.guild.default_role: PermissionOverwrite(view_channel=False),
                interaction.user: PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                target_user: PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                interaction.guild.get_role(self.cog.MOD_ROLE_ID): PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }

            try:
                ticket_channel = await category.create_text_channel(name=channel_name, overwrites=dict(overwrites))
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                await interaction.response.send_message("❌ Недостаточно прав для создания канала.", ephemeral=True)
                logger.error(f"Failed to create ticket channel: {e}")
                return

            embed = Embed(
                title="／ Новый тикет．",
                description=f"Тикет создан пользователем **{escape_mentions(interaction.user.display_name)}**",
                color=0x2B2D31,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="ID тикета", value=f"`#{ticket_id}`", inline=True)
            embed.add_field(name="Нарушитель", value=target_user.mention, inline=True)
            embed.add_field(name="Заявитель", value=interaction.user.mention, inline=True)
            embed.add_field(name="Причина", value=f"**{escape_mentions(self.reason.value)}**", inline=False)
            if self.evidence.value:
                embed.add_field(name="Доказательства", value=f"{escape_mentions(self.evidence.value)}", inline=False)
            embed.set_footer(text=f"ID тикета: {ticket_id}")

            view = self.cog.TicketControlView(ticket_id, interaction.user.id, target_user.id, ticket_channel, self.cog)
            try:
                msg = await ticket_channel.send(content=f"<@&{self.cog.MOD_ROLE_ID}>", embed=embed, view=view)
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                await interaction.response.send_message("❌ Не удалось отправить сообщение в канал.", ephemeral=True)
                logger.error(f"Failed to send ticket message: {e}")
                try:
                    await ticket_channel.delete(reason="Rollback: failed to send message")
                except:
                    pass
                return

            self.cog.view_data[str(msg.id)] = {
                "channel_id": ticket_channel.id,
                "ticket_id": ticket_id,
                "author_id": interaction.user.id,
                "target_id": target_user.id,
                "taken": False,
                "closed": False,
                "messages": []
            }
            self.cog.save_view_data()
            self.cog.bot.add_view(view, message_id=msg.id)

            await interaction.response.send_message(f"✅ Тикет создан! Перейдите в {ticket_channel.mention}", ephemeral=True)

            await self.cog.log_action(
                title="Тикет открыт",
                fields=[
                    ("ID", f"`#{ticket_id}`", True),
                    ("Заявитель", interaction.user.mention, True),
                    ("Нарушитель", target_user.mention, True),
                    ("Причина", escape_mentions(self.reason.value), False)
                ],
                color=0x2B2D31
            )

    class TicketControlView(ui.View):
        def __init__(self, ticket_id: int, author_id: int, target_id: int, channel: nextcord.TextChannel, cog):
            super().__init__(timeout=None)
            self.ticket_id = ticket_id
            self.author_id = author_id
            self.target_id = target_id
            self.channel = channel
            self.cog = cog

        @ui.button(label="Взять в работу", style=ButtonStyle.primary, emoji="📌")
        async def take_button(self, button, interaction):
            if not any(role.id in self.cog.MOD_ROLES_ALLOWED for role in interaction.user.roles):
                await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
                return

            mod_role = interaction.guild.get_role(self.cog.MOD_ROLE_ID)
            if mod_role is None:
                await interaction.response.send_message("❌ Роль модерации не найдена! Обратитесь к администрации.", ephemeral=True)
                return

            overwrites = dict(self.channel.overwrites)
            overwrites[mod_role] = PermissionOverwrite(view_channel=False)
            overwrites[interaction.user] = PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

            try:
                await self.channel.edit(overwrites=overwrites)
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                await interaction.response.send_message("❌ Нет прав на изменение канала.", ephemeral=True)
                logger.error(f"Failed to edit channel: {e}")
                return

            for item in self.children:
                if item.label == "Взять в работу":
                    item.disabled = True

            try:
                await interaction.message.edit(view=self)
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                logger.warning(f"Failed to edit message: {e}")

            msg_id = str(interaction.message.id)
            if msg_id in self.cog.view_data:
                self.cog.view_data[msg_id]["taken"] = True
                self.cog.save_view_data()

            embed = interaction.message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "📌 В работе":
                    embed.set_field_at(i, name="📌 В работе", value=f"Модератор {interaction.user.mention}", inline=False)
                    break
            else:
                embed.add_field(name="📌 В работе", value=f"Модератор {interaction.user.mention}", inline=False)

            try:
                await interaction.message.edit(embed=embed)
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                logger.warning(f"Failed to edit embed: {e}")

            await self.cog.log_action(
                title="Тикет взят в работу",
                fields=[
                    ("ID", f"`#{self.ticket_id}`", True),
                    ("Модератор", interaction.user.mention, True),
                    ("Канал", self.channel.mention, True),
                ],
                color=0xFFA500
            )

            await interaction.response.send_message("📌 Тикет взят в работу!", ephemeral=True)

        @ui.button(label="Закрыть", style=ButtonStyle.danger, emoji="🔒")
        async def close_button(self, button, interaction):
            if not any(role.id in self.cog.MOD_ROLES_ALLOWED for role in interaction.user.roles):
                await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
                return

            log_lines = [
                f"── Лог тикета #{self.ticket_id} ──",
                f"Создан: {interaction.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Закрыт: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
                f"ID тикета: #{self.ticket_id}",
                f"Модератор: {escape_mentions(interaction.user.display_name)} ({interaction.user.id})",
                "",
                "── Сообщения ──"
            ]

            try:
                async for msg in self.channel.history(limit=1000, oldest_first=True):
                    time = msg.created_at.strftime("%H:%M:%S")
                    author = escape_mentions(msg.author.display_name)
                    content = escape_mentions(msg.content[:200].replace("\n", " "))
                    if content:
                        log_lines.append(f"[{time}] {author}: {content}")
                    for embed in msg.embeds:
                        if embed.title:
                            log_lines.append(f"[{time}] {author}: [Embed] {embed.title}")
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                log_lines.append(f"⚠️ Не удалось прочитать историю канала: {e}")

            log_text = "\n".join(log_lines) + "\n\n── Конец лога ──"

            log_channel = self.cog.bot.get_channel(self.cog.LOG_CHANNEL_ID)
            if log_channel:
                with io.StringIO() as f:
                    f.write(log_text)
                    f.seek(0)
                    log_data = f.read().encode("utf-8")
                file = nextcord.File(io.BytesIO(log_data), filename=f"ticket_{self.ticket_id}.txt")
                embed_log = Embed(
                    title="／ Лог тикета．",
                    description=f"Тикет #{self.ticket_id} закрыт модератором {interaction.user.mention}",
                    timestamp=datetime.now(timezone.utc)
                )
                try:
                    await log_channel.send(embed=embed_log, file=file)
                except (nextcord.Forbidden, nextcord.HTTPException) as e:
                    logger.warning(f"Failed to send log: {e}")

            for item in self.children:
                item.disabled = True

            try:
                await interaction.message.edit(view=self)
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                logger.warning(f"Failed to edit message: {e}")

            msg_id = str(interaction.message.id)
            if msg_id in self.cog.view_data:
                self.cog.view_data[msg_id]["closed"] = True
                self.cog.save_view_data()

            close_embed = Embed(
                title="／ Тикет закрыт．",
                description=f"Тикет #{self.ticket_id} закрыт модератором {interaction.user.mention}\nНажмите кнопку ниже, чтобы удалить канал.",
                timestamp=datetime.now(timezone.utc)
            )
            close_view = self.cog.DeleteTicketView(self.channel, self.ticket_id, self.cog)
            try:
                await interaction.channel.send(embed=close_embed, view=close_view)
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                logger.warning(f"Failed to send close message: {e}")

            await self.cog.log_action(
                title="Тикет закрыт",
                fields=[
                    ("ID", f"`#{self.ticket_id}`", True),
                    ("Модератор", interaction.user.mention, True),
                ],
                color=0xFF0000
            )

            await interaction.response.send_message("🔒 Тикет закрыт! Лог сохранён.", ephemeral=True)

    class DeleteTicketView(ui.View):
        def __init__(self, channel, ticket_id: int, cog):
            super().__init__(timeout=None)
            self.channel = channel
            self.ticket_id = ticket_id
            self.cog = cog

        @ui.button(label="Удалить обращение", style=ButtonStyle.danger, emoji="🗑️")
        async def delete_button(self, button, interaction):
            admin_roles = [
                1505229944245059735,
                994284414584504372,
                957679828176367647,
                846338416303538226
            ]
            if not any(role.id in admin_roles for role in interaction.user.roles):
                await interaction.response.send_message("❌ У вас нет прав на удаление тикета!", ephemeral=True)
                return

            await interaction.response.send_message("🗑️ Канал удаляется...", ephemeral=True)

            for msg_id, data in list(self.cog.view_data.items()):
                if data.get("ticket_id") == self.ticket_id:
                    del self.cog.view_data[msg_id]
                    self.cog.save_view_data()
                    break

            try:
                await self.channel.delete(reason=f"Тикет #{self.ticket_id} удалён модератором {interaction.user.name}")
            except (nextcord.Forbidden, nextcord.HTTPException) as e:
                await interaction.followup.send(f"❌ Не удалось удалить канал: {e}", ephemeral=True)

    class CreateTicketView(ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @ui.button(label="Создать тикет", style=ButtonStyle.success, emoji="🎫")
        async def create_ticket(self, button, interaction):
            modal = self.cog.TicketModal(self.cog)
            await interaction.response.send_modal(modal)

    @commands.command(name="ticket_panel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        embed = Embed(
            title="／ Связь с администрацией．",
            description=(
                "**Создание тикета**\n"
                "Тикеты созданы для того, чтобы связываться с администрацией нашего проекта для решения вопроса или подачи жалобы на участника.\n\n"
                "**Причины открытия тикета**\n"
                "• Вопрос к администрации сервера\n"
                "• Жалоба на нарушение в чате/личных сообщениях\n"
                "• Обжалование наказаний, выданных нашими модераторами\n"
                "• Сообщения об ошибках в настройке сервера или его ботов\n\n"
                "**При подаче жалобы обязательно:**\n"
                "• Указать **айди** нарушителя\n"
                "• Написать **причину** подачи жалобы\n"
                "• Прикрепить **доказательства**\n"
                "• Общаться **уважительно**\n\n"
                "**Памятка**\n"
                "• **Ложные/шуточные тикеты** наказываются\n"
                "• Жалоба **без доказательств** не будет удовлетворена\n"
                "• Закрыть тикет имеет право **только** человек из стаффа"
            ),
            color=0x2B2D31
        )
        embed.set_image(url='https://media.discordapp.net/attachments/1033984293543878657/1505237284927180930/8f7e042ae3a21dbb.png?ex=6a5c4ab6&is=6a5af936&hm=c8f3c82fd94bc90677d3d9e075604a990b5f1688a24581588ec928d07dc5d2de&=&format=webp&quality=lossless&width=1102&height=396')

        view = self.CreateTicketView(self)
        try:
            await ctx.send(embed=embed, view=view)
        except (nextcord.Forbidden, nextcord.HTTPException) as e:
            await ctx.send(f"❌ Не удалось отправить панель: {e}")
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Tickets(bot))