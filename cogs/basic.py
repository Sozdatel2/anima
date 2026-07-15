## Импорты библиотек
import nextcord
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

## Импорты из файлов/библиотек
from nextcord.ext import commands
from nextcord import Interaction, SlashOption

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.DATA_PATH = Path(__file__).parent.parent / "data" / "user_statuses.json"
        self.DATA_PATH.parent.mkdir(exist_ok=True)
        
        self.user_statuses = self.load_statuses()
    
    def load_statuses(self):
        """Загружает статусы из файла"""
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_statuses(self):
        """Сохраняет статусы в файл"""
        with open(self.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.user_statuses, f, indent=2, ensure_ascii=False)
    
    def get_status(self, user_id: str) -> str:
        """Получает статус пользователя"""
        data = self.user_statuses.get(user_id, {})
        return data.get("status", "")
    
    def get_last_update(self, user_id: str) -> datetime:
        """Получает время последнего обновления статуса"""
        data = self.user_statuses.get(user_id, {})
        timestamp = data.get("last_update")
        if timestamp:
            return datetime.fromisoformat(timestamp)
        return None
    
    def can_update_status(self, user_id: str) -> bool:
        """Проверяет, можно ли обновить статус (КД 1 час)"""
        last_update = self.get_last_update(user_id)
        if not last_update:
            return True
        return datetime.now(timezone.utc) - last_update >= timedelta(hours=1)
    
    def set_status(self, user_id: str, status: str):
        """Устанавливает статус пользователя"""
        self.user_statuses[user_id] = {
            "status": status,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
        self.save_statuses()
    
    def remove_status(self, user_id: str):
        """Удаляет статус пользователя"""
        if user_id in self.user_statuses:
            del self.user_statuses[user_id]
            self.save_statuses()
            return True
        return False
    
    async def _send_response(self, context, embed, ephemeral=False):
        """Отправляет ответ в зависимости от типа контекста"""
        if isinstance(context, Interaction):
            if ephemeral:
                await context.response.send_message(embed=embed, ephemeral=True)
            else:
                await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)
    
    @nextcord.slash_command(name="user", description="Показать информацию о пользователе")
    async def user_slash(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(
            description="Участник (по умолчанию — вы)",
            required=False
        )
    ):
        if member is None:
            member = interaction.user
        await self._user_command(interaction, member)
    
    @commands.command(name="user", aliases=['u'], description="Показать информацию о пользователе")
    async def user_prefix(self, ctx, member: nextcord.Member = None):
        if member is None:
            member = ctx.author
        await self._user_command(ctx, member)
    
    async def _user_command(self, context, member: nextcord.Member):
        """Основной метод для отображения информации о пользователе"""

        status_map = {
            nextcord.Status.online: "`🟢` В сети",
            nextcord.Status.idle: "`🌙` Не активен",
            nextcord.Status.dnd: "`🔴` Не беспокоить",
            nextcord.Status.offline: "`⚫` Не в сети"
        }
        status = status_map.get(member.status, "`⚫` Не в сети")
        
        highest_role = member.top_role.name if member.top_role.name != "@everyone" else "Нет роли"
        
        user_status = self.get_status(str(member.id))
        
        emb = nextcord.Embed(
            title="／ Информация о пользователе．"
        )
        
        if user_status:
            emb.description = f"-# {user_status}"
        
        emb.set_thumbnail(url=member.display_avatar.url)
        
        emb.add_field(
            name="Ник",
            value=f"`{member.display_name}`",
            inline=True
        )
        emb.add_field(
            name="ID",
            value=f"`{member.id}`",
            inline=True
        )
        emb.add_field(
            name="Статус",
            value=status,
            inline=True
        )
        emb.add_field(
            name="Высшая роль",
            value=f"`{highest_role}`",
            inline=True
        )
        
        if member.joined_at:
            emb.add_field(
                name="Участник с",
                value=f"<t:{int(member.joined_at.timestamp())}:F>",
                inline=False
            )
        
        emb.add_field(
            name="Аккаунт создан",
            value=f"<t:{int(member.created_at.timestamp())}:F>",
            inline=False
        )
        
        if member.banner:
            emb.set_image(url=member.banner.url)
        
        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)
    
    @nextcord.slash_command(name="set-st", description="Установить свой статус")
    async def set_status_slash(
        self,
        interaction: Interaction,
        status: str = SlashOption(
            description="Ваш статус (до 75 символов)",
            required=True,
            max_length=75
        )
    ):
        await self._set_status(interaction, status)
    
    @commands.command(name="set-st", description="Установить свой статус")
    async def set_status_prefix(self, ctx, *, status: str):
        await self._set_status(ctx, status)
    
    async def _set_status(self, context, status: str):
        """Устанавливает статус пользователя"""
        user_id = str(context.author.id if hasattr(context, 'author') else context.user.id)
        
        if len(status) > 75:
            emb = nextcord.Embed(
                description="❌ Статус не может превышать 75 символов．"
            )
            await self._send_response(context, emb, ephemeral=True)
            return
        
        if not self.can_update_status(user_id):
            last_update = self.get_last_update(user_id)
            if last_update:
                next_update = last_update + timedelta(hours=1)
                emb = nextcord.Embed(
                    description=f"⏳ Статус можно будет изменить через\n<t:{int(next_update.timestamp())}:R>"
                )
                await self._send_response(context, emb, ephemeral=True)
                return
        
        self.set_status(user_id, status)
        
        emb = nextcord.Embed(
            description=f"✅ Статус установлен：\n`{status}`"
        )
        await self._send_response(context, emb)
    
    @nextcord.slash_command(name="rm-status", description="Удалить свой статус")
    async def remove_status_slash(self, interaction: Interaction):
        await self._remove_status(interaction)
    
    @commands.command(name="rm-status", description="Удалить свой статус")
    async def remove_status_prefix(self, ctx):
        await self._remove_status(ctx)
    
    async def _remove_status(self, context):
        """Удаляет статус пользователя"""
        user_id = str(context.author.id if hasattr(context, 'author') else context.user.id)
        
        if self.remove_status(user_id):
            emb = nextcord.Embed(
                description="✅ Статус удалён．"
            )
        else:
            emb = nextcord.Embed(
                description="❌ У вас нет установленного статуса．"
            )
        
        await self._send_response(context, emb)
    
    @nextcord.slash_command(name="s-info", description="Показать информацию о сервере")
    async def server_slash(self, interaction: Interaction):
        await self._server_command(interaction)
    
    @commands.command(name="s-info", aliases=["info"], description="Показать информацию о сервере")
    async def server_prefix(self, ctx):
        await self._server_command(ctx)
    
    async def _server_command(self, context):
        """Основной метод для отображения информации о сервере"""
        guild = context.guild
        bots = len(guild.bots)
        users = guild.member_count - bots
        total_members = guild.member_count
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        forums = len(guild.forum_channels)
        stage = len(guild.stage_channels)
        
        total_channels = text_channels + voice_channels + forums + stage
        owner = guild.owner
        created_at = guild.created_at
        created_at_timestamp = int(created_at.timestamp())
        created_at_formatted = f"<t:{created_at_timestamp}:F>"
        
        emb = nextcord.Embed(
            title=f"／ Информация о сервере．"
        )
        if guild.icon:
            emb.set_thumbnail(url=str(guild.icon.url))
        
        emb.add_field(
            name="👥 Участники",
            value=f'Всего： **{total_members}**\nПользователей： **{users}**\nБотов： **{bots}**',
            inline=True
        )
        emb.add_field(
            name="📁 Каналы",
            value=f'Всего： **{total_channels}**\nТекстовых： **{text_channels}**\nГолосовых： **{voice_channels}**\nФорумов： **{forums}**\nТрибун： **{stage}**',
            inline=True
        )
        emb.add_field(
            name="👑 Владелец",
            value=f'{owner.display_name}',
            inline=True
        )
        emb.add_field(
            name="📅 Дата создания",
            value=f'{created_at_formatted}\n<t:{created_at_timestamp}:R>',
            inline=True
        )
        
        if isinstance(context, Interaction):
            await context.response.send_message(embed=emb)
        else:
            await context.send(embed=emb)

def setup(bot):
    bot.add_cog(Basic(bot))