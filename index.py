import asyncio
import main
import config

async def main_async():
    # Starte den Bot
    await main.bot.start(config.TOKEN)

# Füge sicherheitshalber ein Guild-Sync hinzu
@main.bot.event
async def on_ready():
    guild = main.discord.Object(id=config.GUILD_ID)
    await main.bot.tree.sync(guild=guild)  # nur für deinen Server
    print(f"✅ Logged in as {main.bot.user} - Commands synced to guild {config.GUILD_ID}")

# Starte asyncio Event Loop
asyncio.run(main_async())
