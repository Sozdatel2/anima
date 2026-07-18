import nextcord
from nextcord.ext import commands

class HideBanCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="hide-ban", description="Выдать теневой бан участнику")
    @commands.has_any_role(852646039982440500, 846338416303538226, 957679828176367647, 994284414584504372)
    async def hide_ban_slash(
        self, 
        interaction: nextcord.Interaction, 
        member: nextcord.Member,
        reason: str = "Не указана"
    ):
        await self._hide_ban(interaction, member, reason)

    @commands.command(name="hide-ban", aliases=["shadow-ban", "sb", "hb"], description="Выдать теневой бан участнику")
    @commands.has_any_role(852646039982440500, 846338416303538226, 957679828176367647, 994284414584504372)
    async def hide_ban_prefix(self, ctx, member: nextcord.Member, *, reason: str = "Не указана"):
        await self._hide_ban(ctx, member, reason)

    async def _hide_ban(self, context, member: nextcord.Member, reason: str):
        """Основной метод для выдачи теневого бана"""
        add_role_id = 1101859215464747099
        remove_role_ids = [846335308497027122, 1019964836639166525]
        reports_channel_id = 846329342983143434

        # ==========================================
        # 🔹 ПРОВЕРКИ
        # ==========================================

        # Нельзя выдать теневой бан самому себе
        author = context.author if hasattr(context, 'author') else context.user
        if member.id == author.id:
            error_embed = nextcord.Embed(
                title="／ Ошибка．",
                description="❌ Нельзя выдать теневой бан самому себе！",
                color=0xE10000
            )
            if isinstance(context, nextcord.Interaction):
                await context.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await context.send(embed=error_embed)
            return

        # Нельзя выдать теневой бан боту
        if member.bot:
            error_embed = nextcord.Embed(
                title="／ Ошибка．",
                description="❌ Нельзя выдать теневой бан боту！",
                color=0xE10000
            )
            if isinstance(context, nextcord.Interaction):
                await context.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await context.send(embed=error_embed)
            return

        # Нельзя выдать теневой бан администратору
        if member.guild_permissions.administrator:
            error_embed = nextcord.Embed(
                title="／ Ошибка．",
                description="❌ Нельзя выдать теневой бан администратору！",
                color=0xE10000
            )
            if isinstance(context, nextcord.Interaction):
                await context.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await context.send(embed=error_embed)
            return

        # ==========================================
        # 🔹 ВЫДАЧА ТЕНЕВОГО БАНА
        # ==========================================

        try:
            add_role = member.guild.get_role(add_role_id)
            if add_role is None:
                raise ValueError(f"Role with ID {add_role_id} not found")

            await member.add_roles(add_role)
            roles_to_remove = [role for role in member.roles if role.id in remove_role_ids]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            dm_embed = nextcord.Embed(
                title="／ Блокировка доступа．",
                description=f"{member.mention}, вам была выдана блокировка доступа к серверу **anime nom**．"
            )
            dm_embed.add_field(
                name="Обжалование",
                value=f"Для обжалования своего наказания вы можете открыть тикет в канале <#{reports_channel_id}>．\nПомните, что шанс освобождения от наказания не 100％, возможен отказ．",
                inline=False
            )
            dm_embed.add_field(
                name="Причина",
                value=f"**{reason}**",
                inline=False
            )

            dm_sent = False
            try:
                await member.send(embed=dm_embed)
                dm_sent = True
            except:
                dm_sent = False

            # Ответ модератору
            response_embed = nextcord.Embed(
                title="／ Блокировка выдана．"
            )
            response_embed.add_field(
                name="Модератор：",
                value=f"**{author.display_name}**",
                inline=True
            )
            response_embed.add_field(
                name="Нарушитель：",
                value=f"**{member.display_name}**",
                inline=True
            )
            response_embed.add_field(
                name="Причина：",
                value=f"**{reason}**",
                inline=False
            )
            response_embed.add_field(
                name="Уведомление：",
                value=f"Сообщение нарушителю： {'✅ Доставлено！' if dm_sent else '❌ Не доставлено！'}",
                inline=False
            )
            response_embed.set_footer(text="Пожалуйста, не забудьте внести нарушителя в канал нарушений．")

            if isinstance(context, nextcord.Interaction):
                await context.response.send_message(embed=response_embed)
            else:
                await context.send(embed=response_embed)

        except Exception as e:
            error_embed = nextcord.Embed(
                title="／ Ошибка．",
                description=f"❌ Произошла ошибка： {str(e)}",
                color=0xE10000
            )
            if isinstance(context, nextcord.Interaction):
                await context.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await context.send(embed=error_embed)

def setup(bot):
    bot.add_cog(HideBanCommand(bot))