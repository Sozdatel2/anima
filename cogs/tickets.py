import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, ui, Embed, ButtonStyle, PermissionOverwrite
from datetime import datetime, timezone

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TICKET_CHANNEL_ID = 846329342983143434 
        self.TICKET_CATEGORY_ID = 1044213985257459732 
        self.MOD_ROLE_ID = 1019691991707172874
        self.MOD_ROLES_ALLOWED = [
            1019691991707172874,  # Модератор
            1505229944245059735,  # Хед модерации
            994284414584504372,   # Куратор
            957679828176367647,   # Администратор
            846338416303538226    # Овнеры
        ]
        self.LOG_CHANNEL_ID = 1234596840008323162 

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
                await interaction.response.send_message("❌ Не удалось определить пользователя. Введите корректный ID или упоминание.", ephemeral=True)
                return

            target_user = interaction.guild.get_member(target_id)
            if not target_user:
                await interaction.response.send_message("❌ Пользователь не найден на сервере.", ephemeral=True)
                return

            if target_user.id == interaction.user.id:
                await interaction.response.send_message("❌ Нельзя создать тикет на самого себя!", ephemeral=True)
                return

            category = interaction.guild.get_channel(self.cog.TICKET_CATEGORY_ID)
            if not category:
                await interaction.response.send_message("❌ Категория для тикетов не найдена! Сообщите администрации.", ephemeral=True)
                return

            ticket_id = int(datetime.now(timezone.utc).timestamp()) % 1000000
            channel_name = f"тикет-{ticket_id}"

            overwrites = {
                interaction.guild.default_role: PermissionOverwrite(view_channel=False),
                interaction.user: PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                target_user: PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                interaction.guild.get_role(self.cog.MOD_ROLE_ID): PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }

            ticket_channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)

            embed = Embed(
                title="／ Новый тикет．",
                description=f"Тикет создан пользователем **{interaction.user.display_name}**",
                color=0x2B2D31,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="ID тикета", value=f"`#{ticket_id}`", inline=True)
            embed.add_field(name="Нарушитель", value=target_user.mention, inline=True)
            embed.add_field(name="Заявитель", value=interaction.user.mention, inline=True)
            embed.add_field(name="Причина", value=f"**{self.reason.value}**", inline=False)
            if self.evidence.value:
                embed.add_field(name="Доказательства", value=f"{self.evidence.value}", inline=False)
            embed.set_footer(text=f"ID тикета: {ticket_id}")

            view = self.cog.TicketControlView(ticket_id, interaction.user.id, target_user.id, ticket_channel, self.cog)
            await ticket_channel.send(content=f"<@&{self.cog.MOD_ROLE_ID}>", embed=embed, view=view)

            await interaction.response.send_message(f"✅ Тикет создан! Перейдите в {ticket_channel.mention}", ephemeral=True)

            await self.cog.log_action(
                title="Тикет открыт",
                fields=[
                    ("ID", f"`#{ticket_id}`", True),
                    ("Заявитель", interaction.user.mention, True),
                    ("Нарушитель", target_user.mention, True),
                    ("Причина", self.reason.value, False)
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
        async def take_button(self, interaction: Interaction, _):
            if not any(role.id in self.cog.MOD_ROLES_ALLOWED for role in interaction.user.roles):
                await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
                return

            mod_role = interaction.guild.get_role(self.cog.MOD_ROLE_ID)
            overwrites = self.channel.overwrites
            overwrites[mod_role] = PermissionOverwrite(view_channel=False)
            overwrites[interaction.user] = PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            await self.channel.edit(overwrites=overwrites)

            for item in self.children:
                if item.label == "Взять в работу":
                    item.disabled = True
            await interaction.message.edit(view=self)

            embed = interaction.message.embeds[0]
            embed.add_field(name="📌 В работе", value=f"Модератор {interaction.user.mention}", inline=False)
            await interaction.message.edit(embed=embed)

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
        async def close_button(self, interaction: Interaction, _):
            if not any(role.id in self.cog.MOD_ROLES_ALLOWED for role in interaction.user.roles):
                await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
                return

            await self.channel.delete(reason=f"Тикет #{self.ticket_id} закрыт модератором {interaction.user.name}")

            await self.cog.log_action(
                title="Тикет закрыт",
                fields=[
                    ("ID", f"`#{self.ticket_id}`", True),
                    ("Модератор", interaction.user.mention, True),
                ],
                color=0xFF0000
            )

            await interaction.response.send_message("🔒 Тикет закрыт!", ephemeral=True)

    class CreateTicketView(ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @ui.button(label="Создать тикет", style=ButtonStyle.success, emoji="🎫")
        async def create_ticket(self, interaction: Interaction, _):
            modal = self.cog.TicketModal(self.cog)
            await interaction.response.send_modal(modal)

    @commands.command(name="ticket_panel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx):
        """Отправляет панель с кнопкой создания тикета (только для админов)"""
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
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Tickets(bot))