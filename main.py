import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from discord.ui import View, Select
from keep_alive import keep_alive
import asyncio

keep_alive()
# --- Constants ---
TEST_GUILD_ID = 1263242458096206004  # Replace with your server ID
ASSISTANCE_CHANNEL_ID = 1392213371914555402  # Replace with your assistance channel ID
EMBED_BANNER_URL = "https://cdn.discordapp.com/attachments/1392213371914555402/1404225638507876432/ACRP_-_Assistance.png"  # Large banner image URL

DARK_GRAY = discord.Color(0x242429)  # Your requested color #242429


# --- Ticket Category Select Menu ---
class TicketCategorySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Support", description="General questions and help", emoji="💬"),
            discord.SelectOption(label="HR Support", description="Staff and human resources related", emoji="🧑‍💼"),
            discord.SelectOption(label="Player Reports", description="Report player misconduct", emoji="🚨"),
            discord.SelectOption(label="Technical Issues", description="Bugs, glitches, or connection problems", emoji="🛠️"),
            discord.SelectOption(label="Appeals & Reviews", description="Ban appeals or dispute resolution", emoji="⚖️"),
            discord.SelectOption(label="Event Coordination", description="Questions about events", emoji="📅"),
            discord.SelectOption(label="Account & Access", description="Login, roles, or permissions issues", emoji="🔐"),
            discord.SelectOption(label="Other Inquiries", description="Any other questions or requests", emoji="❓"),
        ]
        super().__init__(
            placeholder="Select a ticket category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        guild = interaction.guild
        user = interaction.user

        # Check if user already has a ticket channel open
        existing_channel = discord.utils.get(
            guild.text_channels,
            name__startswith=f"ticket-{user.name.lower()}"
        )
        if existing_channel:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing_channel.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        sanitized_category = category.lower().replace(" ", "-").replace("&", "and")
        channel_name = f"ticket-{user.name.lower()}-{sanitized_category}"
        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=(
                f"Thank you {user.mention} for contacting support.\n"
                f"**Category:** {category}\n"
                "Our team will assist you shortly."
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(
            f"Your ticket has been created: {ticket_channel.mention}",
            ephemeral=True
        )

class TicketCreationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


# --- Discord Bot setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory store for ticket claims: channel_id -> user_id
claimed_tickets = {}


@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    # Wait a bit to ensure cache ready
    await asyncio.sleep(3)

    guild = discord.Object(id=TEST_GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print(f"Commands synced to guild {TEST_GUILD_ID}!")

    # Send or refresh the assistance embed with ticket category dropdown
    await send_assistance_embed(bot, ASSISTANCE_CHANNEL_ID)


async def send_assistance_embed(bot, channel_id):
    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"❌ Channel ID {channel_id} not found or inaccessible!")
        return

    try:
        # Delete previous bot messages in Assistance channel to keep it clean
        async for message in channel.history(limit=50):
            if message.author == bot.user:
                await message.delete()

        # Embed 1: Large full-width banner image only (no title or description)
        banner_embed = discord.Embed(color=DARK_GRAY)
        banner_embed.set_image(url=EMBED_BANNER_URL)

        # Embed 2: Welcome embed below banner
        welcome_embed = discord.Embed(
            title="Welcome to American Capital Roleplay Support",
            description=(
                "Welcome to the official support center for American Capital Roleplay.\n\n"
                "Our dedicated team is here to assist you with any issues, questions, or concerns "
                "you might have. To get started, please select a relevant ticket category from "
                "the dropdown menu below. This will help us direct your request to the appropriate team "
                "member and provide you with faster assistance.\n\n"
                "Thank you for being a valued member of our community!"
            ),
            color=DARK_GRAY
        )
        welcome_embed.set_footer(text="American Capital Roleplay Support • We’re here to help!")

        # Embed 3: Categories list with bullet points
        categories_description = (
            "**Please select a ticket category below to create a support ticket:**\n\n"
            "• 💬 **General Support** — General questions and help\n"
            "• 🧑‍💼 **HR Support** — Staff and human resources related\n"
            "• 🚨 **Player Reports** — Report player misconduct\n"
            "• 🛠️ **Technical Issues** — Bugs, glitches, or connection problems\n"
            "• ⚖️ **Appeals & Reviews** — Ban appeals or dispute resolution\n"
            "• 📅 **Event Coordination** — Questions about events\n"
            "• 🔐 **Account & Access** — Login, roles, or permissions issues\n"
            "• ❓ **Other Inquiries** — Any other questions or requests\n"
        )
        category_embed = discord.Embed(
            title="Support Ticket Categories",
            description=categories_description,
            color=DARK_GRAY
        )
        category_embed.set_footer(text="Select the appropriate category from the dropdown menu below.")

        view = TicketCreationView()

        # Send banner embed separately for full width
        await channel.send(embed=banner_embed)

        # Send welcome and category embeds together with the dropdown view
        await channel.send(embeds=[welcome_embed, category_embed], view=view)

        print("✅ Assistance embeds sent successfully!")

    except Exception as e:
        print(f"❌ Error sending assistance embeds: {e}")


# --- Slash command: create ticket (manual) ---
@bot.tree.command(name="ticket", description="Create a support ticket")
@app_commands.describe(reason="Reason for creating the ticket")
async def ticket(interaction: discord.Interaction, reason: str = "No reason provided"):
    guild = interaction.guild
    user = interaction.user

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    ticket_channel = await guild.create_text_channel(f"ticket-{user.name}", overwrites=overwrites)

    embed = discord.Embed(
        title="🎫 New Ticket Created",
        description=f"**Reason:** {reason}\n**Created by:** {user.mention}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Ticket ID: {ticket_channel.id}")
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await ticket_channel.send(embed=embed)
    await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)


# --- Slash command: close ticket ---
@bot.tree.command(name="close", description="Close this ticket (staff only)")
async def close(interaction: discord.Interaction):
    channel = interaction.channel
    member = interaction.user

    if not member.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission to close tickets.", ephemeral=True)
        return

    await interaction.response.send_message(f"Closing ticket {channel.mention}...", ephemeral=True)
    await channel.delete()


# --- Slash command: add user to ticket ---
@bot.tree.command(name="add", description="Add a user to this ticket (staff only)")
@app_commands.describe(user="User to add to the ticket")
async def add(interaction: discord.Interaction, user: discord.Member):
    channel = interaction.channel
    member = interaction.user

    if not member.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission to add users.", ephemeral=True)
        return

    overwrite = channel.overwrites_for(user)
    overwrite.read_messages = True
    overwrite.send_messages = True

    await channel.set_permissions(user, overwrite=overwrite)
    await interaction.response.send_message(f"{user.mention} was added to the ticket.", ephemeral=True)


# --- Slash command: remove user from ticket ---
@bot.tree.command(name="remove", description="Remove a user from this ticket (staff only)")
@app_commands.describe(user="User to remove from the ticket")
async def remove(interaction: discord.Interaction, user: discord.Member):
    channel = interaction.channel
    member = interaction.user

    if not member.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission to remove users.", ephemeral=True)
        return

    overwrite = channel.overwrites_for(user)
    overwrite.read_messages = False
    overwrite.send_messages = False

    await channel.set_permissions(user, overwrite=overwrite)
    await interaction.response.send_message(f"{user.mention} was removed from the ticket.", ephemeral=True)


# --- Slash command: show ticket info ---
@bot.tree.command(name="info", description="Show information about this ticket")
async def info(interaction: discord.Interaction):
    channel = interaction.channel

    if not channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ This command can only be used in ticket channels.", ephemeral=True)
        return

    created_at = channel.created_at.strftime("%Y-%m-%d %H:%M UTC")
    overwrites = channel.overwrites

    allowed_members = [
        str(target) for target, perm in overwrites.items()
        if isinstance(target, discord.Member) and perm.read_messages
    ]

    embed = discord.Embed(title=f"Ticket Info: {channel.name}", color=DARK_GRAY)
    embed.add_field(name="Created At", value=created_at)
    embed.add_field(name="Allowed Users", value=", ".join(allowed_members) or "None")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Slash command: claim ticket ---
@bot.tree.command(name="claim", description="Claim this ticket to handle it (staff only)")
async def claim(interaction: discord.Interaction):
    channel = interaction.channel
    member = interaction.user

    if not member.guild_permissions.manage_channels:
        await interaction.response.send_message("❌ You don't have permission to claim tickets.", ephemeral=True)
        return

    claimed_tickets[channel.id] = member.id
    await interaction.response.send_message(f"{member.mention} has claimed this ticket.", ephemeral=False)


# --- Optional: Command to repost the assistance embed manually ---
@bot.tree.command(name="sendembed", description="Repost the assistance embed in the assistance channel (admin only)")
async def sendembed(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    await send_assistance_embed(bot, ASSISTANCE_CHANNEL_ID)
    await interaction.response.send_message("✅ Assistance embed has been reposted.", ephemeral=True)


# --- Run ---
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
