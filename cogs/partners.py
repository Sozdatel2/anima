import nextcord
from nextcord.ext import commands
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path
from nextcord import SlashOption

class Partnerships(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CHANNEL_ID = 850588016862822430
        self.ROLE_ID = 1090070131939475558
        self.GUILD_ID = 798974707880689664
        
        self.DATA_PATH = Path(__file__).parent.parent / "data" / "partnerships.json"
        self.DATA_PATH.parent.mkdir(exist_ok=True) 
        
        self.data = self.load_data()
    
    def load_data(self):
        try:
            with open(self.DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "partnerships": {},
                "servers": {},
                "meta": {"first_run": datetime.now(timezone.utc).isoformat()}
            }
    
    def save_data(self):
        with open(self.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get_period_stats(self, period):
        now = datetime.now(timezone.utc)
        stats = {"users": {}, "servers": {}, "total": 0}
        
        for user_id, user_data in self.data["partnerships"].items():
            user_stats = {"count": 0, "servers": set()}
            
            for i, timestamp in enumerate(user_data["timestamps"]):
                ts = datetime.fromisoformat(timestamp)
                
                if period == "day" and (now - ts) > timedelta(days=1):
                    continue
                elif period == "week" and (now - ts) > timedelta(weeks=1):
                    continue
                elif period == "month" and (now - ts) > timedelta(days=30):
                    continue
                
                user_stats["count"] += 1
                user_stats["servers"].add(user_data["servers"][i])
                stats["total"] += 1
            
            if user_stats["count"] > 0:
                stats["users"][user_id] = user_stats
        
        for user_stats in stats["users"].values():
            for server in user_stats["servers"]:
                stats["servers"][server] = stats["servers"].get(server, 0) + 1
        
        return stats
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != self.CHANNEL_ID:
            return
        
        if not any(role.id == self.ROLE_ID for role in message.author.roles):
            return
        
        invites = re.findall(r"https?://discord\.gg/([a-zA-Z0-9]+)", message.content)
        if not invites:
            return
        
        user_id = str(message.author.id)
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if user_id not in self.data["partnerships"]:
            self.data["partnerships"][user_id] = {
                "count": 0,
                "servers": [],
                "timestamps": []
            }
        
        for invite in invites:
            self.data["partnerships"][user_id]["count"] += 1
            self.data["partnerships"][user_id]["servers"].append(invite)
            self.data["partnerships"][user_id]["timestamps"].append(timestamp)
            self.data["servers"][invite] = self.data["servers"].get(invite, 0) + 1
        
        self.save_data()
    
    @nextcord.slash_command(name="partners", description="Статистика партнёрств")
    @commands.has_permissions(administrator=True)
    async def partners(
        self,
        interaction: nextcord.Interaction,
        period: str = SlashOption(
            description="Период статистики",
            choices={"День": "day", "Неделя": "week", "Месяц": "month", "Всё время": "all"},
            required=True
        )
    ):
        await interaction.response.defer()
        
        stats = self.get_period_stats(period)
        period_names = {"day": "День", "week": "Неделя", "month": "Месяц", "all": "Всё время"}
        
        embed = nextcord.Embed(
            title="／ Статистика партнёрств．",
            description=f"-# {period_names.get(period, period)}\nВсего： **{stats['total']}**"
        )
        
        top_servers = sorted(stats["servers"].items(), key=lambda x: x[1], reverse=True)[:5]
        if top_servers:
            embed.add_field(
                name="Топ серверов",
                value="\n".join(f"`{s}` — {c}" for s, c in top_servers),
                inline=False
            )
        else:
            embed.add_field(
                name="Топ серверов",
                value="Нет данных",
                inline=False
            )
        
        guild = self.bot.get_guild(self.GUILD_ID)
        if guild:
            for user_id, user_stats in stats["users"].items():
                user = guild.get_member(int(user_id))
                if user:
                    embed.add_field(
                        name=f"**{user.display_name}**",
                        value=f"Партнёрств： {user_stats['count']}\nСерверов： {len(user_stats['servers'])}",
                        inline=True
                    )
        
        if not stats["users"]:
            embed.add_field(
                name="Сотрудники",
                value="Нет активности за этот период",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

def setup(bot):
    bot.add_cog(Partnerships(bot))