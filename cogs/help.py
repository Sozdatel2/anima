import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from typing import Union, Dict, List

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.excluded_commands = ['load', 'unload', 'reload', 'help']
        
        self.category_map = {
            'Moderation': {'emoji': '🛡️', 'name': 'Модерация'},
            'Verify': {'emoji': '✅', 'name': 'Верификация'},
            'Partnerships': {'emoji': '🤝', 'name': 'Партнёрства'},
            'Basic': {'emoji': '📋', 'name': 'Основные'},
            'Stats': {'emoji': '📊', 'name': 'Статистика'},
            'Nokta': {'emoji': '📌', 'name': 'Нокты'},
            'HideBanCommand': {'emoji': '👻', 'name': 'Скрытый бан'},
            'Reports': {'emoji': '📩', 'name': 'Репорты'},
            'Tickets': {'emoji': '🎫', 'name': 'Тикеты'},
            'Default': {'emoji': '📂', 'name': 'Прочее'}
        }

    @nextcord.slash_command(name="help", description="Показать список доступных команд")
    async def help_slash(self, interaction: Interaction):
        await self._help_command(interaction)

    @commands.command(name="help", aliases=["h", "помощь"], description="Показать список доступных команд")
    async def help_prefix(self, ctx):
        await self._help_command(ctx)

    async def _help_command(self, context: Union[Interaction, commands.Context]):
        embed = nextcord.Embed(
            title="／ Список команд бота．",
            description="Команды разделены по категориям．Отображаются только доступные вам команды．"
        )

        user = context.user if isinstance(context, Interaction) else context.author
        permissions = user.guild_permissions if hasattr(user, 'guild_permissions') else None
        
        categorized_commands = self._get_categorized_commands(user, permissions)
        
        for category, commands_list in categorized_commands.items():
            if commands_list:
                category_info = self.category_map.get(category, {'emoji': '📂', 'name': 'Прочее'})
                embed.add_field(
                    name=f"{category_info['emoji']} {category_info['name']}",
                    value="\n".join(commands_list),
                    inline=False
                )

        if not any(categorized_commands.values()):
            embed.add_field(
                name="Нет доступных команд",
                value="У вас нет прав на использование ни одной команды бота．",
                inline=False
            )

        embed.set_footer(
            text=f"Используйте {self.bot.command_prefix}help [команда] или /help для подробностей"
        )

        if isinstance(context, Interaction):
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)

    def _get_categorized_commands(self, user, permissions) -> Dict[str, List[str]]:
        categorized = {category: [] for category in self.category_map.keys()}
        categorized['Default'] = []
        
        for cmd in self.bot.commands:
            if self._should_exclude_command(cmd):
                continue
            if not self._has_permission_for_command(cmd, user, permissions):
                continue
            category = self._get_command_category(cmd)
            command_text = self._format_prefix_command(cmd)
            categorized[category].append(command_text)
        
        try:
            for cmd in self._get_slash_commands():
                if cmd.name in self.excluded_commands:
                    continue
                if not self._has_slash_permission(cmd, user):
                    continue
                category = self._get_command_category(cmd)
                command_text = self._format_slash_command(cmd)
                categorized[category].append(command_text)
        except Exception as e:
            print(f"Ошибка при получении slash-команд: {e}")
        
        return categorized

    def _should_exclude_command(self, cmd) -> bool:
        return cmd.name in self.excluded_commands or cmd.hidden

    def _has_permission_for_command(self, cmd, user, permissions) -> bool:
        if not cmd.checks:
            return True
        for check in cmd.checks:
            if hasattr(check, '__closure__'):
                try:
                    if 'permissions' in str(check.__closure__):
                        if permissions and permissions.administrator:
                            return True
                        return False
                except:
                    pass
        for check in cmd.checks:
            if hasattr(check, '__name__') and check.__name__ == 'has_role':
                if permissions and (permissions.administrator or permissions.manage_guild):
                    return True
        if permissions and permissions.administrator:
            return True
        return False

    def _has_slash_permission(self, cmd, user) -> bool:
        if hasattr(cmd, 'default_member_permissions'):
            if cmd.default_member_permissions:
                perms = cmd.default_member_permissions
                if hasattr(user, 'guild_permissions'):
                    if user.guild_permissions.administrator:
                        return True
                    for perm in perms:
                        if not getattr(user.guild_permissions, perm, False):
                            return False
        return True

    def _get_command_category(self, cmd) -> str:
        if hasattr(cmd, 'cog_name') and cmd.cog_name:
            if cmd.cog_name in self.category_map:
                return cmd.cog_name
        if hasattr(cmd, 'cog'):
            cog_name = type(cmd.cog).__name__
            if cog_name in self.category_map:
                return cog_name
        for category in ['Moderation', 'Verify', 'Partnerships', 'Basic', 'Stats', 'Nokta', 'HideBanCommand', 'Reports', 'Tickets']:
            if category.lower() in cmd.name.lower():
                return category
        return 'Default'

    def _format_prefix_command(self, cmd) -> str:
        aliases = f" (Алиасы： {', '.join(cmd.aliases)})" if cmd.aliases else ""
        description = cmd.help or cmd.description or 'Описание отсутствует'
        return f"**`{self.bot.command_prefix}{cmd.name}`**{aliases} — {description}"

    def _format_slash_command(self, cmd) -> str:
        params = ""
        if hasattr(cmd, 'options') and cmd.options:
            params = " " + " ".join(f"[{param.name}]" for param in cmd.options)
        description = cmd.description or 'Описание отсутствует'
        return f"**`/{cmd.name}{params}`** — {description}"

    def _get_slash_commands(self):
        slash_commands = []
        if hasattr(self.bot, 'slash_commands'):
            for cmd_name, cmd in self.bot.slash_commands.items():
                if hasattr(cmd, 'name'):
                    slash_commands.append(cmd)
        else:
            for cog in self.bot.cogs.values():
                if hasattr(cog, 'get_application_commands'):
                    for cmd in cog.get_application_commands():
                        if hasattr(cmd, 'name'):
                            slash_commands.append(cmd)
        return slash_commands

def setup(bot):
    bot.add_cog(HelpCommand(bot))