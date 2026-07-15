import nextcord
from nextcord.ext import commands
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path

class Partnerships(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CHANNEL_ID = 850588016862822430
        self.ROLE_ID = 1090070131939475558
        self.GUILD_ID = 798974707880689664
        self.VIP_SERVER_NAME = "Каталог серверов"
        
        self.DATA_PATH = Path(__file__).parent.parent / "data" / "partnerships.json"
        self.DATA_PATH.parent.mkdir(exist_ok=True)
        
        self.data = self.load_data()
        self.server_cache = {}
    
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
    
    def get_server_name(self, invite_code):
        if invite_code in self.server_cache:
            return self.server_cache[invite_code]
        
        if invite_code in self.data.get("server_names", {}):
            name = self.data["server_names"][invite_code]
            self.server_cache[invite_code] = name
            return name
        
        try:
            invite = self.bot.fetch_invite(invite_code)
            name = invite.guild.name
            self.server_cache[invite_code] = name
            
            if "server_names" not in self.data:
                self.data["server_names"] = {}
            self.data["server_names"][invite_code] = name
            self.save_data()
            
            return name
        except:
            self.server_cache[invite_code] = invite_code
            return invite_code
    
    def get_user_stats(self, user_id, period="all"):
        now = datetime.now(timezone.utc)
        user_data = self.data["partnerships"].get(str(user_id))
        
        if not user_data:
            return {"count": 0, "servers": [], "timestamps": [], "server_names": []}
        
        filtered = {"count": 0, "servers": [], "timestamps": [], "server_names": []}
        
        for i, timestamp in enumerate(user_data["timestamps"]):
            ts = datetime.fromisoformat(timestamp)
            
            if period == "day" and (now - ts) > timedelta(days=1):
                continue
            elif period == "week" and (now - ts) > timedelta(weeks=1):
                continue
            elif period == "month" and (now - ts) > timedelta(days=30):
                continue
            
            filtered["count"] += 1
            filtered["servers"].append(user_data["servers"][i])
            filtered["timestamps"].append(timestamp)
            
            server_name = self.get_server_name(user_data["servers"][i])
            filtered["server_names"].append(server_name)
        
        return filtered
    
    def get_all_stats(self, period="all"):
        now = datetime.now(timezone.utc)
        stats = {}
        
        for user_id, user_data in self.data["partnerships"].items():
            filtered = {"count": 0, "servers": [], "timestamps": [], "server_names": []}
            
            for i, timestamp in enumerate(user_data["timestamps"]):
                ts = datetime.fromisoformat(timestamp)
                
                if period == "day" and (now - ts) > timedelta(days=1):
                    continue
                elif period == "week" and (now - ts) > timedelta(weeks=1):
                    continue
                elif period == "month" and (now - ts) > timedelta(days=30):
                    continue
                
                filtered["count"] += 1
                filtered["servers"].append(user_data["servers"][i])
                filtered["timestamps"].append(timestamp)
                
                server_name = self.get_server_name(user_data["servers"][i])
                filtered["server_names"].append(server_name)
            
            if filtered["count"] > 0:
                stats[user_id] = filtered
        
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
    
    # ==========================================
    # 🔹 ПРЕФИКСНЫЕ КОМАНДЫ (через .)
    # ==========================================
    
    @commands.command(
        name="pm_info",
        aliases=["pminfo", "pmstat", "pm"],
        description="Показывает статистику ПМа (по умолчанию — себя)",
        brief="Статистика ПМа"
    )
    async def pm_info(self, ctx, member: nextcord.Member = None):
        """／ Статистика ПМа．"""
        if member is None:
            member = ctx.author
        
        if not any(role.id == self.ROLE_ID for role in member.roles):
            await ctx.send(f"❌ {member.mention} не является ПМом!")
            return
        
        stats = self.get_user_stats(member.id, "all")
        
        embed = nextcord.Embed(
            title="／ Статистика ПМа．",
            description=(
                f"**{member.display_name}**\n"
                f"Всего партнёрств： **{stats['count']}**\n"
                f"Уникальных серверов： **{len(set(stats['server_names']))}**"
            ),
            color=member.color
        )
        
        if stats["server_names"]:
            server_counts = {}
            for server_name in stats["server_names"]:
                server_counts[server_name] = server_counts.get(server_name, 0) + 1
            
            top_servers = sorted(server_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            embed.add_field(
                name="／ Чаще всего писал．",
                value="\n".join(f"◞ **{name}** — {count}" for name, count in top_servers),
                inline=False
            )
        else:
            embed.add_field(
                name="／ Чаще всего писал．",
                value="Нет данных",
                inline=False
            )
        
        if stats["server_names"]:
            recent = list(zip(stats["server_names"], stats["timestamps"]))[-5:][::-1]
            embed.add_field(
                name="／ Последние．",
                value="\n".join(f"◞ **{name}** — <t:{int(datetime.fromisoformat(ts).timestamp())}:R>" 
                               for name, ts in recent),
                inline=False
            )
        else:
            embed.add_field(
                name="／ Последние．",
                value="Нет данных",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="pm_top",
        aliases=["pmtop", "pmleaderboard", "pmlb"],
        description="Показывает топ ПМов по количеству партнёрств",
        brief="Топ ПМов"
    )
    async def pm_top(self, ctx):
        """／ Топ ПМов．"""
        stats = self.get_all_stats("all")
        
        if not stats:
            await ctx.send("／ Статистика．\n\nНет данных о партнёрствах")
            return
        
        embed = nextcord.Embed(
            title="／ Топ ПМов．",
            description=f"Всего ПМов с активностью： **{len(stats)}**",
            color=0x2B2D31
        )
        
        guild = self.bot.get_guild(self.GUILD_ID)
        if guild:
            sorted_users = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
            
            top_text = []
            for i, (user_id, user_stats) in enumerate(sorted_users[:10], 1):
                member = guild.get_member(int(user_id))
                if member:
                    unique_servers = len(set(user_stats["server_names"]))
                    medal = ["**1．**", "**2．**", "**3．**"][i-1] if i <= 3 else f"**{i}．**"
                    top_text.append(
                        f"{medal} {member.mention}\n"
                        f"   ◞ Партнёрств： {user_stats['count']} | Серверов： {unique_servers}"
                    )
            
            if top_text:
                embed.description += f"\n\n" + "\n".join(top_text)
            else:
                embed.add_field(
                    name="Нет данных",
                    value="Не удалось получить информацию о пользователях",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="pm_servers",
        aliases=["pmservers", "pmserver", "pmsrv"],
        description="Показывает топ серверов по количеству партнёрств",
        brief="Топ серверов"
    )
    async def pm_servers(self, ctx):
        """／ Топ серверов．"""
        if not self.data["servers"]:
            await ctx.send("／ Статистика．\n\nНет данных о серверах")
            return
        
        sorted_servers = sorted(self.data["servers"].items(), key=lambda x: x[1], reverse=True)
        
        embed = nextcord.Embed(
            title="／ Топ серверов．",
            description=f"Всего серверов： **{len(sorted_servers)}**",
            color=0x2B2D31
        )
        
        server_list = []
        vip_added = False
        
        for invite_code, count in sorted_servers[:15]:
            name = self.get_server_name(invite_code)
            
            if name == self.VIP_SERVER_NAME and not vip_added:
                server_list.insert(0, f"◞ **{name}** — {count} партнёрств")
                vip_added = True
            else:
                server_list.append(f"◞ **{name}** — {count}")
        
        if not vip_added:
            for invite_code, count in self.data["servers"].items():
                name = self.get_server_name(invite_code)
                if name == self.VIP_SERVER_NAME:
                    server_list.insert(0, f"◞ **{name}** — {count} партнёрств")
                    break
        
        if len(sorted_servers) > 15:
            server_list.append(f"\n*и ещё {len(sorted_servers) - 15} серверов*")
        
        embed.description += f"\n\n" + "\n".join(server_list)
        
        await ctx.send(embed=embed)
    
    @commands.command(
        name="pm_reset",
        aliases=["resetpartners", "pmclear"],
        description="Полный сброс всей статистики партнёрств",
        brief="Сброс партнёрств"
    )
    @commands.has_permissions(administrator=True)
    async def pm_reset(self, ctx):
        """／ Сброс статистики партнёрств．"""
        
        await ctx.send(
            "／ Подтверждение．\n\n"
            "Ты уверен, что хочешь **полностью сбросить** всю статистику партнёрств?\n"
            "Это действие **необратимо**.\n\n"
            "Для подтверждения введи `!yes` в течение **30 секунд**."
        )
        
        def check(m):
            return m.author == ctx.author and m.content.lower() == "!yes" and m.channel == ctx.channel
        
        try:
            await ctx.bot.wait_for("message", check=check, timeout=30.0)
        except TimeoutError:
            await ctx.send("／ Отменено．\n\nВремя вышло, сброс отменён.")
            return
        
        self.data = {
            "partnerships": {},
            "servers": {},
            "meta": {"reset_at": datetime.now(timezone.utc).isoformat()}
        }
        self.save_data()
        
        self.server_cache = {}
        
        await ctx.send(
            "／ Готово．\n\n"
            "Статистика партнёрств **полностью сброшена**."
        )
    
    # ==========================================
    # 🔹 СЛЕШ-КОМАНДЫ (/)
    # ==========================================
    
    @nextcord.slash_command(name="pm_info", description="Показывает статистику ПМа")
    @commands.has_permissions(administrator=True)
    async def slash_pm_info(
        self,
        interaction: nextcord.Interaction,
        member: nextcord.Member = nextcord.SlashOption(
            description="Пользователь (по умолчанию — вы)",
            required=False
        )
    ):
        if member is None:
            member = interaction.user
        
        if not any(role.id == self.ROLE_ID for role in member.roles):
            await interaction.response.send_message(f"❌ {member.mention} не является ПМом!", ephemeral=True)
            return
        
        stats = self.get_user_stats(member.id, "all")
        
        embed = nextcord.Embed(
            title="／ Статистика ПМа．",
            description=(
                f"**{member.display_name}**\n"
                f"Всего партнёрств： **{stats['count']}**\n"
                f"Уникальных серверов： **{len(set(stats['server_names']))}**"
            ),
            color=member.color
        )
        
        if stats["server_names"]:
            server_counts = {}
            for server_name in stats["server_names"]:
                server_counts[server_name] = server_counts.get(server_name, 0) + 1
            
            top_servers = sorted(server_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            embed.add_field(
                name="／ Чаще всего писал．",
                value="\n".join(f"◞ **{name}** — {count}" for name, count in top_servers),
                inline=False
            )
        else:
            embed.add_field(
                name="／ Чаще всего писал．",
                value="Нет данных",
                inline=False
            )
        
        if stats["server_names"]:
            recent = list(zip(stats["server_names"], stats["timestamps"]))[-5:][::-1]
            embed.add_field(
                name="／ Последние．",
                value="\n".join(f"◞ **{name}** — <t:{int(datetime.fromisoformat(ts).timestamp())}:R>" 
                               for name, ts in recent),
                inline=False
            )
        else:
            embed.add_field(
                name="／ Последние．",
                value="Нет данных",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(name="pm_top", description="Показывает топ ПМов по количеству партнёрств")
    @commands.has_permissions(administrator=True)
    async def slash_pm_top(self, interaction: nextcord.Interaction):
        stats = self.get_all_stats("all")
        
        if not stats:
            await interaction.response.send_message("／ Статистика．\n\nНет данных о партнёрствах")
            return
        
        embed = nextcord.Embed(
            title="／ Топ ПМов．",
            description=f"Всего ПМов с активностью： **{len(stats)}**",
            color=0x2B2D31
        )
        
        guild = self.bot.get_guild(self.GUILD_ID)
        if guild:
            sorted_users = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
            
            top_text = []
            for i, (user_id, user_stats) in enumerate(sorted_users[:10], 1):
                member = guild.get_member(int(user_id))
                if member:
                    unique_servers = len(set(user_stats["server_names"]))
                    medal = ["**1．**", "**2．**", "**3．**"][i-1] if i <= 3 else f"**{i}．**"
                    top_text.append(
                        f"{medal} {member.mention}\n"
                        f"   ◞ Партнёрств： {user_stats['count']} | Серверов： {unique_servers}"
                    )
            
            if top_text:
                embed.description += f"\n\n" + "\n".join(top_text)
            else:
                embed.add_field(
                    name="Нет данных",
                    value="Не удалось получить информацию о пользователях",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(name="pm_servers", description="Показывает топ серверов по количеству партнёрств")
    @commands.has_permissions(administrator=True)
    async def slash_pm_servers(self, interaction: nextcord.Interaction):
        if not self.data["servers"]:
            await interaction.response.send_message("／ Статистика．\n\nНет данных о серверах")
            return
        
        sorted_servers = sorted(self.data["servers"].items(), key=lambda x: x[1], reverse=True)
        
        embed = nextcord.Embed(
            title="／ Топ серверов．",
            description=f"Всего серверов： **{len(sorted_servers)}**",
            color=0x2B2D31
        )
        
        server_list = []
        vip_added = False
        
        for invite_code, count in sorted_servers[:15]:
            name = self.get_server_name(invite_code)
            
            if name == self.VIP_SERVER_NAME and not vip_added:
                server_list.insert(0, f"◞ **{name}** — {count} партнёрств")
                vip_added = True
            else:
                server_list.append(f"◞ **{name}** — {count}")
        
        if not vip_added:
            for invite_code, count in self.data["servers"].items():
                name = self.get_server_name(invite_code)
                if name == self.VIP_SERVER_NAME:
                    server_list.insert(0, f"◞ **{name}** — {count} партнёрств")
                    break
        
        if len(sorted_servers) > 15:
            server_list.append(f"\n*и ещё {len(sorted_servers) - 15} серверов*")
        
        embed.description += f"\n\n" + "\n".join(server_list)
        
        await interaction.response.send_message(embed=embed)

def setup(bot):
    bot.add_cog(Partnerships(bot))