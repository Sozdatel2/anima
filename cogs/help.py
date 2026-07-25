import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed
from typing import Union, Dict, List
import traceback

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

    @commands.command(name="help", aliases=["h", "помощь"], description="Показать список доступных команд")
    async def help_prefix(self, ctx, command_name: str = None):
        try:
            if command_name:
                await self._help_command_detail(ctx, command_name)
            else:
                await self._help_command(ctx)
        except Exception as e:
            embed = Embed(
                title="／ Ошибка．",
                description=f"❌ Произошла ошибка при отображении справки:\n```py\n{e}\n```"
            )
            await ctx.send(embed=embed)

    @nextcord.slash_command(name="help", description="Показать список доступных команд")
    async def help_slash(
        self,
        interaction: Interaction,
        command: str = SlashOption(
            required=False,
            description="Название команды для получения подробной информации"
        )
    ):
        try:
            if command:
                await self._help_command_detail(interaction, command)
            else:
                await self._help_command(interaction)
        except Exception as e:
            error_text = traceback.format_exc()
            embed = Embed(
                title="／ Ошибка．",
                description=f"❌ Произошла ошибка:\n```py\n{error_text[:1900]}\n```"
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

    async def _help_command_detail(self, context, command_name: str):
        cmd = self.bot.get_command(command_name)

        if not cmd:
            embed = Embed(
                title="／ Ошибка．",
                description=f"❌ Команда `{command_name}` не найдена"
            )
            if isinstance(context, Interaction):
                await context.response.send_message(embed=embed, ephemeral=True)
            else:
                await context.send(embed=embed)
            return

        prefix = self.bot.command_prefix
        if callable(prefix):
            try:
                prefix = prefix(self.bot, None) if hasattr(prefix, '__call__') else '.'
            except:
                prefix = '.'

        if isinstance(prefix, list):
            prefix = prefix[0] if prefix else '.'

        aliases = f"**{', '.join(cmd.aliases)}**" if cmd.aliases else "Нет"
        description = cmd.help or cmd.description or "Описание отсутствует"
        usage = f"{prefix}{cmd.name}"

        params = []
        try:
            for param in cmd.params.values():
                if param.name not in ['self', 'ctx', 'interaction']:
                    if param.default == param.empty:
                        params.append(f"[{param.name}]")
                    else:
                        params.append(f"({param.name})")
            if params:
                usage += " " + " ".join(params)
        except:
            pass

        checks = []
        for check in cmd.checks:
            check_str = str(check)
            if 'has_permissions' in check_str:
                checks.append("Требуются права модератора")
            elif 'is_owner' in check_str:
                checks.append("Только для владельца бота")
            elif 'has_role' in check_str:
                checks.append("Требуется определённая роль")

        embed = Embed(
            title=f"／ Помощь по команде．",
            description=f"**{cmd.name}**"
        )
        embed.add_field(name="Описание", value=description, inline=False)
        embed.add_field(name="Использование", value=f"`{usage}`", inline=False)
        embed.add_field(name="Алиасы", value=aliases, inline=True)
        if checks:
            embed.add_field(name="Права", value="\n".join(checks), inline=True)

        try:
            slash_cmd = None
            for cmd_obj in self.bot.application_commands:
                if hasattr(cmd_obj, 'name') and cmd_obj.name == command_name:
                    slash_cmd = cmd_obj
                    break

            if slash_cmd:
                slash_usage = f"/{slash_cmd.name}"
                try:
                    if hasattr(slash_cmd, 'options') and slash_cmd.options:
                        for opt in slash_cmd.options:
                            if getattr(opt, 'required', False):
                                slash_usage += f" [{opt.name}]"
                            else:
                                slash_usage += f" ({opt.name})"
                except:
                    pass
                embed.add_field(name="Слеш-команда", value=f"`{slash_usage}`", inline=False)
        except:
            pass

        if isinstance(context, Interaction):
            await context.response.send_message(embed=embed)
        else:
            await context.send(embed=embed)

    async def _help_command(self, context: Union[Interaction, commands.Context]):
        embed = Embed(
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
            text=f"Используйте {self.bot.command_prefix}help [команда] или /help [команда] для подробностей"
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
            for cmd in self.bot.application_commands:
                if hasattr(cmd, 'name') and cmd.name in self.excluded_commands:
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
        return cmd.name in self.excluded_commands or getattr(cmd, 'hidden', False)

    def _has_permission_for_command(self, cmd, user, permissions) -> bool:
        if not cmd.checks:
            return True
        if permissions and permissions.administrator:
            return True
        return False

    def _has_slash_permission(self, cmd, user) -> bool:
        try:
            if hasattr(cmd, 'default_member_permissions'):
                perms = cmd.default_member_permissions
                if perms:
                    if hasattr(user, 'guild_permissions'):
                        if user.guild_permissions.administrator:
                            return True
                        for perm, value in perms:
                            if not getattr(user.guild_permissions, perm, False):
                                return False
            return True
        except:
            return True

    def _get_command_category(self, cmd) -> str:
        try:
            if hasattr(cmd, 'cog_name') and cmd.cog_name:
                if cmd.cog_name in self.category_map:
                    return cmd.cog_name
            if hasattr(cmd, 'cog'):
                cog_name = type(cmd.cog).__name__
                if cog_name in self.category_map:
                    return cog_name
        except:
            pass

        for category in ['Moderation', 'Verify', 'Partnerships', 'Basic', 'Stats', 'Nokta', 'HideBanCommand', 'Reports', 'Tickets']:
            if category.lower() in cmd.name.lower():
                return category
        return 'Default'

    def _format_prefix_command(self, cmd) -> str:
        aliases = f" (Алиасы： {', '.join(cmd.aliases)})" if cmd.aliases else ""
        description = cmd.help or cmd.description or 'Описание отсутствует'
        return f"**`{self.bot.command_prefix}{cmd.name}`**{aliases} — {description}"

    def _format_slash_command(self, cmd) -> str:
        try:
            params = ""
            if hasattr(cmd, 'options') and cmd.options:
                params = " " + " ".join(f"[{opt.name}]" for opt in cmd.options)
            description = getattr(cmd, 'description', 'Описание отсутствует')
            return f"**`/{cmd.name}{params}`** — {description}"
        except:
            return f"**`/{cmd.name}`**"

def setup(bot):
    bot.add_cog(HelpCommand(bot))