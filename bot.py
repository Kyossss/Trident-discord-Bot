import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import asyncio
from typing import Optional
import re

import config
import storage
import scraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BuiltByBitBot')

class BBBBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await storage.init_db()
        await self.tree.sync(guild=discord.Object(id=config.GUILD_ID))
        self.poll_resources.start()
        logger.info("Bot setup complete. Polling task started.")

    @tasks.loop(minutes=config.POLL_INTERVAL_MINUTES)
    async def poll_resources(self):
        logger.info("Running scheduled poll of resources...")
        await check_all_resources(self)

    @poll_resources.before_loop
    async def before_poll(self):
        await self.wait_until_ready()

bot = BBBBot()

async def check_all_resources(bot_client: BBBBot):
    resources = await storage.get_all_resources()
    if not resources:
        logger.info("No resources tracked.")
        return

    guild = bot_client.get_guild(config.GUILD_ID)
    if not guild:
        logger.error(f"Guild {config.GUILD_ID} not found.")
        return

    forum_channel = guild.get_channel(config.FORUM_CHANNEL_ID)
    if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
        logger.error(f"Forum channel {config.FORUM_CHANNEL_ID} not found or is not a forum.")
        return

    for res in resources:
        try:
            logger.info(f"Checking resource: {res['nickname']} ({res['resource_id']})")
            details = await scraper.get_resource_details(res['resource_id'], res['slug'])
            
            if not details:
                logger.warning(f"Failed to scrape {res['nickname']}")
                continue
            
            new_version = details['version']
            
            # If version is empty, maybe parsing failed, avoid posting empty updates
            if not new_version:
                logger.warning(f"Could not parse version for {res['nickname']}. Skipping.")
                continue

            last_known = res['last_known_version']
            
            if new_version != last_known:
                logger.info(f"Update detected for {res['nickname']}: {last_known} -> {new_version}")
                
                # Check if forum thread exists, if not create one
                thread_id = res['forum_thread_id']
                thread = guild.get_thread(thread_id) if thread_id else None
                
                embed = discord.Embed(
                    title=f"Update: {details['title']}",
                    url=details['url'],
                    color=discord.Color.blue()
                )
                if details['thumbnail']:
                    embed.set_thumbnail(url=details['thumbnail'])
                
                embed.add_field(name="New Version", value=new_version, inline=True)
                if details['date']:
                    embed.add_field(name="Date", value=details['date'], inline=True)
                
                if details['changelog']:
                    embed.add_field(name="Changelog Excerpt", value=details['changelog'], inline=False)
                
                if not thread:
                    # Create thread
                    logger.info(f"Creating new thread for {res['nickname']}")
                    thread_with_message = await forum_channel.create_thread(
                        name=res['nickname'],
                        content=f"Tracking updates for {details['title']}",
                        embed=embed
                    )
                    thread = thread_with_message.thread
                    await storage.update_resource_state(res['resource_id'], new_version, thread.id)
                else:
                    # Post in existing thread
                    await thread.send(embed=embed)
                    await storage.update_resource_state(res['resource_id'], new_version)

        except Exception as e:
            logger.error(f"Error checking {res['nickname']}: {e}", exc_info=True)
            
        # Polite spacing
        await asyncio.sleep(2)


# --- Slash Commands ---
@bot.tree.command(name="track", description="Track a new BuiltByBit resource", guild=discord.Object(id=config.GUILD_ID))
@app_commands.describe(url="The BuiltByBit resource URL", nickname="A nickname for the forum thread")
async def track_cmd(interaction: discord.Interaction, url: str, nickname: str):
    # e.g., https://builtbybit.com/resources/my-plugin-name.12345/
    match = re.search(r'resources/([^/]+)\.(\d+)/?', url)
    if not match:
        await interaction.response.send_message("Invalid URL format. Expected: `https://builtbybit.com/resources/slug.id/`", ephemeral=True)
        return
        
    slug = match.group(1)
    resource_id = int(match.group(2))
    
    await interaction.response.defer()
    
    await storage.add_resource(resource_id, slug, nickname)
    
    # Try fetching right away to get initial version
    details = await scraper.get_resource_details(resource_id, slug)
    if details and details['version']:
        # Create thread immediately
        guild = interaction.guild
        forum = guild.get_channel(config.FORUM_CHANNEL_ID)
        
        if forum and isinstance(forum, discord.ForumChannel):
            embed = discord.Embed(title=f"Now Tracking: {details['title']}", url=details['url'], color=discord.Color.green())
            embed.add_field(name="Current Version", value=details['version'])
            if details['thumbnail']:
                embed.set_thumbnail(url=details['thumbnail'])
                
            thread_with_message = await forum.create_thread(
                name=nickname,
                content=f"Tracking updates for {details['title']}",
                embed=embed
            )
            await storage.update_resource_state(resource_id, details['version'], thread_with_message.thread.id)
            await interaction.followup.send(f"Successfully tracking {nickname}. Thread created!")
        else:
            await interaction.followup.send(f"Tracking {nickname} (Current Version: {details['version']}), but couldn't create thread (check FORUM_CHANNEL_ID).")
    else:
        await interaction.followup.send(f"Added {nickname} to DB, but failed to fetch data immediately. Will try again next poll.")


@bot.tree.command(name="untrack", description="Stop tracking a BuiltByBit resource", guild=discord.Object(id=config.GUILD_ID))
async def untrack_cmd(interaction: discord.Interaction, nickname: str):
    removed = await storage.remove_resource(nickname)
    if removed:
        await interaction.response.send_message(f"Stopped tracking {nickname}.")
    else:
        await interaction.response.send_message(f"Resource {nickname} not found.", ephemeral=True)

@bot.tree.command(name="list", description="List all tracked resources", guild=discord.Object(id=config.GUILD_ID))
async def list_cmd(interaction: discord.Interaction):
    resources = await storage.get_all_resources()
    if not resources:
        await interaction.response.send_message("Not tracking any resources.", ephemeral=True)
        return
        
    lines = []
    for r in resources:
        lines.append(f"**{r['nickname']}** (ID: {r['resource_id']}) - Last version: `{r['last_known_version']}`")
        
    await interaction.response.send_message("\n".join(lines))

@bot.tree.command(name="checknow", description="Force check all resources immediately (Admin only)", guild=discord.Object(id=config.GUILD_ID))
@app_commands.default_permissions(administrator=True)
async def checknow_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("Forcing immediate check of all resources in the background...", ephemeral=True)
    asyncio.create_task(check_all_resources(bot))


from keep_alive import keep_alive

if __name__ == "__main__":
    if not config.DISCORD_BOT_TOKEN or config.DISCORD_BOT_TOKEN == "your_bot_token_here":
        logger.error("Please configure DISCORD_BOT_TOKEN in .env")
    else:
        keep_alive()
        bot.run(config.DISCORD_BOT_TOKEN)
