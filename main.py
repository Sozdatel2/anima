## Импорты библиотек
import os
import nextcord
from itertools import cycle
import asyncio

## Импорты из файлов/библиотек
from nextcord.ext import commands
from settings import prefix
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TOKEN")
GUILD_ID = 798974707880689664 

bot = commands.Bot(command_prefix=prefix, owner_id=942776739870933003, intents=nextcord.Intents.all())
bot.remove_command("help")

async def update_member_count():
    await bot.wait_until_ready()
    
    statuses = cycle([
        lambda: nextcord.Activity(
            type=nextcord.ActivityType.watching, 
            name="anime nom"
        ),
        lambda: nextcord.Activity(
            type=nextcord.ActivityType.listening, 
            name=f"{sum(guild.member_count for guild in bot.guilds)} прекрасных голоса(-ов)"
        )
    ])
    
    while not bot.is_closed():
        current_status = next(statuses)()
        await bot.change_presence(
            activity=current_status,
            status=nextcord.Status.idle
        )
        await asyncio.sleep(15)

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