# BuiltByBit Discord Bot

A Discord bot that monitors BuiltByBit resource pages and announces updates in a Discord Forum Channel. It circumvents simple bot protections by using `curl_cffi` to mimic Chrome's TLS fingerprint.

## Setup

1. Make sure you have Python 3.11+ installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in the values:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token.
   - `GUILD_ID`: The ID of your Discord server.
   - `FORUM_CHANNEL_ID`: The ID of the Forum Channel where threads will be posted.
   - `POLL_INTERVAL_MINUTES`: How often to check for updates (default: 60).

## Creating the Discord Bot
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new Application and add a Bot.
3. Enable the **Message Content Intent** in the Bot settings.
4. Invite the bot to your server with the following permissions:
   - Send Messages
   - Create Public Threads
   - Send Messages in Threads
   - Embed Links

## Finding Resource ID and Slug
When you visit a BuiltByBit resource, the URL looks like this:
`https://builtbybit.com/resources/my-awesome-plugin.12345/`
- Slug: `my-awesome-plugin`
- ID: `12345`

Use the full URL when using the `/track` command.

## Running the Bot
```bash
python bot.py
```

## Running Tests
To run the scraper unit tests against the local fixture without hitting the live site:
```bash
pytest tests/test_scraper.py
```
