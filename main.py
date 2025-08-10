# acrp_inbox.py
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

@bot.command()
async def ticket(ctx, *, reason="No reason provided"):
    guild = ctx.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    ticket_channel = await guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites)
    embed = discord.Embed(title="New Ticket", description=reason, color=discord.Color.blue())
    await ticket_channel.send(embed=embed)
    await ctx.send(f"{ctx.author.mention}, your ticket has been created: {ticket_channel.mention}")

bot.run("MTQwNDE5NzgyNDY1NjMxNDU0OQ.GGYYll.iAbzZknPrUFqLAO6UNEn5UBUWNf2nCiZjYs96M")
