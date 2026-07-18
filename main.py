## Импорты библиотек
import os
import nextcord
import traceback
import asyncio
from itertools import cycle

## Импорты из файлов/библиотек
from nextcord.ext import commands
from settings import prefix
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TOKEN")
GUILD_ID = 798974707880689664 
OWNER_ID = 942776739870933003

bot = commands.Bot(command_prefix=prefix, owner_id=OWNER_ID, intents=nextcord.Intents.all())
bot.remove_command("help")

async def send_error_to_owner(error: Exception, ctx=None, interaction=None):
    """Отправляет ошибку в ЛС владельцу"""
    try:
        user = await bot.fetch_user(OWNER_ID)
        if not user:
            return
        
        error_text = f"**／ Ошибка．**\n\n```py\n{traceback.format_exc()[:1900]}\n```"
        
        if ctx:
            error_text += f"\n**Команда:** `{ctx.command.name if ctx.command else 'Неизвестно'}`"
            error_text += f"\n**Автор:** {ctx.author}"
            error_text += f"\n**Канал:** {ctx.channel}"
        elif interaction:
            error_text += f"\n**Команда:** `/{interaction.application_command.name if interaction.application_command else 'Неизвестно'}`"
            error_text += f"\n**Автор:** {interaction.user}"
            error_text += f"\n**Канал:** {interaction.channel}"
        
        await user.send(error_text)
    except:
        pass

@bot.event
async def on_command_error(ctx, error):
    """Обработка ошибок для префиксных команд"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    await send_error_to_owner(error, ctx=ctx)
    
    print(f"Ошибка в команде {ctx.command}: {error}")

@bot.event
async def on_interaction_error(interaction: nextcord.Interaction, error: Exception):
    """Обработка ошибок для слеш-команд"""
    await send_error_to_owner(error, interaction=interaction)
    
    if not interaction.response.is_done():
        await interaction.response.send_message("❌ Произошла ошибка. Администрация уже уведомлена.", ephemeral=True)
    
    print(f"Ошибка в слеш-команде {interaction.application_command.name if interaction.application_command else 'Неизвестно'}: {error}")

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

for fn in os.listdir("./cogs"):
    if fn.endswith(".py"):
        try:
            bot.load_extension(f"cogs.{fn[:-3]}")
            print(f"✅ Загружен ког: {fn}")
        except Exception as e:
            print(f"❌ Ошибка загрузки {fn}: {e}")

@bot.command()
@commands.is_owner()
async def load(ctx, extension):
    bot.load_extension(f"cogs.{extension}")
    await ctx.send('Loaded extention!')

@bot.command()
@commands.is_owner()
async def unload(ctx, extension):
    bot.unload_extension(f"cogs.{extension}")
    await ctx.send('Unloaded extention!')

@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    bot.reload_extension(f"cogs.{extension}")
    await ctx.send('Reloaded extention!')

bot.run(token)