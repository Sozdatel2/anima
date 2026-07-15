import nextcord
from nextcord.ext import commands
from nextcord import Interaction

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="verify", description="Верифицироваться на сервере")
    @commands.has_role(1019964836639166525)
    async def verify_slash(self, interaction: Interaction):
        await self._verify_command(interaction)

    @commands.command(name="verify", description="Верифицирует пользователя на сервере")
    @commands.has_role(1019964836639166525)
    async def verify_prefix(self, ctx):
        await self._verify_command(ctx)

    async def _verify_command(self, context):
        """Основной метод для верификации"""
        guild = context.guild
        chat_id = 1029838738848743494
        chat = guild.get_channel(chat_id)
        
        not_lover_id = 1019964836639166525
        lover_id = 846335308497027122
        not_lover = guild.get_role(not_lover_id)
        lover = guild.get_role(lover_id)

        try:
            if isinstance(context, Interaction):
                await context.response.defer(ephemeral=True)
                await context.delete_original_response()
            else:
                await context.message.delete()
        except:
            pass

        await context.author.remove_roles(not_lover)
        await context.author.add_roles(lover)

        emb = nextcord.Embed(
            description="／ Встреча．\n\n**Охаё**, путник(-ца)! Ты попал на **anime nom**．\n**Уютный** и **дружелюбный** сервер, на котором ты можешь найти себе компанию по душе！\nПеред началом общения **необходимо** ознакомиться с правилами в этих каналах：\n\n◞ <#846329639533281281>\n◞ <#1228686033218965534>"
        )
        emb.set_image(url='https://media.discordapp.net/attachments/1033984293543878657/1508834272302075986/c33242b1d4f817fd.png?ex=6a16faeb&is=6a15a96b&hm=2f4ffca6258e50bba7e48a6827a75b1d3a2d4ebc18dd338bdfdc2ea41a630a9f&=&format=webp&quality=lossless&width=1102&height=396')

        await chat.send(
            content=f'{context.author.mention} <@&1044238189512097842> <@&1001198066428289084>',
            embed=emb,
            delete_after=150
        )

        if isinstance(context, Interaction):
            await context.followup.send("✅ Вы успешно верифицированы！", ephemeral=True)

def setup(bot):
    bot.add_cog(Verify(bot))