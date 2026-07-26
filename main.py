import datetime
import os
import nextcord
import traceback
import asyncio

from itertools import cycle
from difflib import get_close_matches
from nextcord.ext import commands
from settings import prefix
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TOKEN")
GUILD_ID = 798974707880689664 
OWNER_ID = 942776739870933003

bot = commands.Bot(command_prefix=prefix, owner_id=OWNER_ID, intents=nextcord.Intents.all())
bot.remove_command("help")

async def send_to_owner(text: str):
    try:
        user = await bot.fetch_user(OWNER_ID)
        if user:
            await user.send(text)
    except:
        pass

def load_cogs():
    loaded = []
    failed = []

    for fn in os.listdir("./cogs"):
        if fn.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{fn[:-3]}")
                loaded.append(f"✅ {fn}")
                print(f"✅ Загружен ког: {fn}")
            except Exception as e:
                error_text = f"❌ Ошибка загрузки {fn}\n```py\n{traceback.format_exc()[:1500]}\n```"
                failed.append(error_text)
                print(f"❌ Ошибка загрузки {fn}: {e}")

    if loaded or failed:
        msg = "**／ Загрузка когов．**\n\n"
        if loaded:
            msg += "**Успешно загружены:**\n" + "\n".join(loaded) + "\n\n"
        if failed:
            msg += "**⚠️ Ошибки загрузки:**\n" + "\n".join(failed)
        bot.loop.create_task(send_to_owner(msg))

load_cogs()

async def send_error_to_owner(error: Exception, ctx=None, interaction=None):
    try:
        user = await bot.fetch_user(OWNER_ID)
        if not user:
            return

        full_traceback = traceback.format_exc()
        if not full_traceback or full_traceback == "NoneType: None\n":
            full_traceback = f"{type(error).__name__}: {str(error)}"

        error_text = f"**／ Ошибка．**\n\n```py\n{full_traceback[:1900]}\n```"

        if ctx:
            error_text += f"\n**Команда:** `{ctx.command.name if ctx.command else 'Неизвестно'}`"
            error_text += f"\n**Автор:** {ctx.author}"
            error_text += f"\n**Канал:** {ctx.channel}"
            error_text += f"\n**Сообщение:** `{ctx.message.content}`"
        elif interaction:
            error_text += f"\n**Команда:** `/{interaction.application_command.name if interaction.application_command else 'Неизвестно'}`"
            error_text += f"\n**Автор:** {interaction.user}"
            error_text += f"\n**Канал:** {interaction.channel}"

        await user.send(error_text)
    except Exception as e:
        print(f"Не удалось отправить ошибку в ЛС: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        command_name = ctx.message.content.split()[0].lstrip(ctx.prefix)
        
        if command_name == "help" or command_name.startswith("help"):
            return
        
        all_commands = [cmd.name for cmd in bot.commands if not cmd.hidden]
        all_commands.extend([alias for cmd in bot.commands for alias in cmd.aliases])
        
        matches = get_close_matches(command_name, all_commands, n=3, cutoff=0.6)
        
        embed = nextcord.Embed(
            title="／ Неизвестная команда．",
            description=f"❌ Команда `{ctx.prefix}{command_name}` не найдена"
        )
        embed.add_field(
            name="💡 Возможно, вы имели в виду",
            value="\n".join([f"`{ctx.prefix}{cmd}`" for cmd in matches]) if matches else f"Используйте `{ctx.prefix}help` для просмотра всех команд",
            inline=False
        )
        embed.set_footer(text="Для получения справки введите .help")
        
        await ctx.send(embed=embed)
        return

    await send_error_to_owner(error, ctx=ctx)

    embed = nextcord.Embed(
        title="／ Ошибка．",
        description="❌ Произошла непредвиденная ошибка.\nАдминистрация уже уведомлена."
    )
    await ctx.send(embed=embed)

@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, error: Exception):
    await send_error_to_owner(error, interaction=interaction)

    embed = nextcord.Embed(
        title="／ Ошибка．",
        description="❌ Произошла непредвиденная ошибка.\nАдминистрация уже уведомлена."
    )

    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)

async def update_member_count():
    await bot.wait_until_ready()

    statuses = cycle([
        lambda: nextcord.Activity(
            type=nextcord.ActivityType.watching,
            name="anime nom"
        ),
        lambda: nextcord.Activity(
            type=nextcord.ActivityType.listening,
            name=f"{sum(guild.member_count for guild in bot.guilds) - 5} прекрасных голоса(-ов)"
        )
    ])

    while not bot.is_closed():
        try:
            current_status = next(statuses)()
            await bot.change_presence(
                activity=current_status,
                status=nextcord.Status.idle
            )
            await asyncio.sleep(15)
        except (ConnectionResetError, ConnectionError, nextcord.GatewayNotFound):
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️ Ошибка обновления статуса: {e}")
            await asyncio.sleep(10)

@bot.event
async def on_ready():
    bot.loop.create_task(update_member_count())

    try:
        await bot.sync_application_commands()
        print("✅ Команды синхронизированы")
    except Exception as e:
        print(f"⚠️ Ошибка синхронизации: {e}")

    print('Bot is ready to work')

@bot.command()
@commands.is_owner()
async def load(ctx, extension):
    try:
        bot.load_extension(f"cogs.{extension}")
        await ctx.send(f'✅ Ког {extension} загружен')
    except Exception as e:
        await ctx.send(f'❌ Ошибка: {e}')

@bot.command()
@commands.is_owner()
async def unload(ctx, extension):
    try:
        bot.unload_extension(f"cogs.{extension}")
        await ctx.send(f'✅ Ког {extension} выгружен')
    except Exception as e:
        await ctx.send(f'❌ Ошибка: {e}')

@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    try:
        bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f'✅ Ког {extension} перезагружен')
    except Exception as e:
        await ctx.send(f'❌ Ошибка: {e}')

@bot.command(name="list_cogs")
@commands.is_owner()
async def list_cogs(ctx):
    """Показывает список загруженных и доступных когов"""
    loaded = list(bot.extensions.keys())
    available = [f[:-3] for f in os.listdir("./cogs") if f.endswith(".py")]

    embed = nextcord.Embed(
        title="／ Список когов．",
        timestamp=datetime.now(datetime.timezone.utc)
    )
    embed.add_field(
        name="✅ Загружены",
        value="\n".join([f"`{cog}`" for cog in loaded]) if loaded else "Нет",
        inline=True
    )
    embed.add_field(
        name="📁 Доступны",
        value="\n".join([f"`{cog}`" for cog in available]) if available else "Нет",
        inline=True
    )
    await ctx.send(embed=embed)

bot.run(token)