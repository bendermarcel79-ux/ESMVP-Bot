import discord
from discord.ext import commands
from discord import app_commands
import config
import io
from datetime import datetime

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(RoleView())
    bot.add_view(TicketView())
    bot.add_view(TicketControlView())
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ---------------- EMBEDS ----------------
def rules_embed():
    return discord.Embed(
        title=config.RULES_TITLE,
        description=config.RULES_TEXT,
        color=config.RULES_COLOR
    )

def roles_embed():
    return discord.Embed(
        title="🎭 Role Selection",
        description="Click a button to **add or remove** a role.",
        color=discord.Color.blurple()
    )

def ticket_embed():
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Select a ticket type from the dropdown below.",
        color=discord.Color.green()
    )

    # 🔥 GROSSES LOGO UNTEN (NICHT thumbnail)
    embed.set_image(url=config.SERVER_LOGO_URL)

    return embed

# ---------------- ROLE VIEW ----------------
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(self, interaction, role_id, name):
        role = interaction.guild.get_role(role_id)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                f"❌ **{name}** role removed.",
                ephemeral=True
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                f"✅ **{name}** role added.",
                ephemeral=True
            )

    @discord.ui.button(label="🚔 Prisoner", style=discord.ButtonStyle.secondary, custom_id="role_prisoner")
    async def prisoner(self, interaction, button):
        await self.toggle_role(interaction, config.PRISONER_ROLE_ID, "Prisoner")

    @discord.ui.button(label="🛡️ Officer", style=discord.ButtonStyle.primary, custom_id="role_officer")
    async def officer(self, interaction, button):
        await self.toggle_role(interaction, config.OFFICER_ROLE_ID, "Officer")

    @discord.ui.button(label="📢 Announcements", style=discord.ButtonStyle.success, custom_id="role_announcements")
    async def announcements(self, interaction, button):
        await self.toggle_role(interaction, config.ANNOUNCEMENTS_ROLE_ID, "Announcements")

# ---------------- TICKET DROPDOWN ----------------
class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", emoji="🛠️", value="support"),
            discord.SelectOption(label="Report", emoji="🚨", value="report"),
            discord.SelectOption(label="Application", emoji="📄", value="application"),
        ]

        super().__init__(
            placeholder="Select a ticket type…",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="ticket_type_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]

        category = guild.get_channel(config.TICKET_CATEGORIES[ticket_type])
        staff_role = guild.get_role(config.STAFF_ROLE_ID)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category
        )

        await channel.set_permissions(user, read_messages=True, send_messages=True)
        await channel.set_permissions(staff_role, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title="🎟️ Support Ticket",
            description="Please describe your issue.\nA staff member will assist you when available.",
            color=discord.Color.blurple()
        )

        # Logo im Ticket bleibt wie vorher (Thumbnail)
        embed.set_thumbnail(url=config.SERVER_LOGO_URL)

        await channel.send(
            content=staff_role.mention,
            embed=embed,
            view=TicketControlView()
        )

        await interaction.followup.send(
            "✅ Your ticket has been created.",
            ephemeral=True
        )

# ---------------- TICKET VIEW ----------------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

# ---------------- TICKET CONTROL VIEW ----------------
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed_by = None

    @discord.ui.button(label="📌 Claim Ticket", style=discord.ButtonStyle.primary, custom_id="claim_ticket")
    async def claim(self, interaction, button):
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Only staff members can claim tickets.",
                ephemeral=True
            )
            return

        if self.claimed_by:
            await interaction.response.send_message(
                "❌ This ticket is already claimed.",
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user.id
        button.disabled = True
        await interaction.message.edit(view=self)

        await interaction.channel.send(
            f"📌 Ticket claimed by {interaction.user.mention}"
        )
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close(self, interaction, button):
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ Only staff members can close tickets.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        messages = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            messages.append(
                f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{msg.author}: {msg.content}"
            )

        transcript = "\n".join(messages)
        file = discord.File(
            io.StringIO(transcript),
            filename=f"{interaction.channel.name}-transcript.txt"
        )

        log_channel = interaction.guild.get_channel(config.LOG_CHANNEL_ID)

        embed = discord.Embed(
            title="📄 Ticket Transcript",
            description=f"Channel: {interaction.channel.name}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed, file=file)
        await interaction.channel.delete()

# ---------------- /panel COMMAND ----------------
@bot.tree.command(name="panel", description="Send rules, roles and ticket panels")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    await interaction.channel.send(embed=rules_embed())
    await interaction.channel.send(embed=roles_embed(), view=RoleView())
    await interaction.channel.send(embed=ticket_embed(), view=TicketView())

    await interaction.response.send_message(
        "✅ Panels sent successfully.",
        ephemeral=True
    )

bot.run(config.TOKEN)
