from discord.ext import commands
import asyncio
from discord_music_core.musicbot import MusicBot


class Music(commands.Cog):
    """Music related commands."""

    def __init__(self, bot):
        self.bot = bot
    
    async def _join_vc(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("You're not connected to a voice channel.")
            return

        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            if ctx.voice_client.channel == channel:
                return channel
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"Moved to {channel.name}")
        else:
            await channel.connect()
            await ctx.send(f"Joined {channel.name}")

        return channel

    @commands.command(help="Joins your voice channel")
    async def join(self, ctx):
        await self._join_vc(ctx)

    @commands.command(help="Stops playback and leaves the current voice channel")
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("I'm not in a voice channel.")
            return

        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")

    @commands.command(help="Play a song from a YouTube URL or search query")
    async def play(self, ctx, *, url: str):
        await self._join_vc(ctx)

        # Pass the current voice client to MusicBot if you haven't already
        if not hasattr(ctx.bot, "musicbot"):
            loop = asyncio.get_running_loop()
            ctx.bot.musicbot = MusicBot(ctx.voice_client, loop)
        else:
            # Update voice client if changed
            if ctx.bot.musicbot.voice_client != ctx.voice_client:
                ctx.bot.musicbot.voice_client = ctx.voice_client

        # Use your MusicBot instance to queue the song
        title = await ctx.bot.musicbot.play(url)

        if title is not None:
            await ctx.send(f"Added to queue: {title}")
        else:
            await ctx.send(f"No song matching '{url}' found.")

    @commands.command(help="Skips current song.")
    async def skip(self, ctx):
        if not hasattr(self.bot, "musicbot"):
            await ctx.send("Music bot is not initialized.")
            return

        self.bot.musicbot.skip()
        await ctx.send("Skipped the current song.")

    @commands.command(aliases=["now"], help="Shows the current song playing.")
    async def nowplaying(self, ctx):
        if not hasattr(self.bot, "musicbot"):
            await ctx.send("Music bot is not initialized.")
            return

        current = self.bot.musicbot.get_current()
        if current:
            await ctx.send(f"Currently playing: {current}")
        else:
            await ctx.send("No song is currently playing.")

    @commands.command(aliases=["list"], help="Shows the titles in the queue.")
    async def queue(self, ctx):
        if not hasattr(self.bot, "musicbot"):
            await ctx.send("Music bot is not initialized.")
            return

        queue_items = self.bot.musicbot.get_queue()
        if not queue_items:
            await ctx.send("The queue is empty.")
            return

        # queue_items are tuples (url, title), so just get titles:
        titles = [title for url, title in queue_items]

        await ctx.send("Queue:\n" + "\n".join(f"- `{title}`" for title in titles))

    @commands.command(help="Stops music playback and clears the queue.")
    async def stop(self, ctx):
        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.stop()
        else:
            await ctx.send("Music bot is not initialized.")

    @commands.command(help="Pauses music.")
    async def pause(self, ctx):
        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.pause()
            await ctx.send("Playback paused.")
        else:
            await ctx.send("Music bot is not initialized.")

    @commands.command(help="Resumes music.")
    async def resume(self, ctx):
        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.resume()
            await ctx.send("Playback resumed.")
        else:
            await ctx.send("Music bot is not initialized.")

async def setup(bot):
    await bot.add_cog(Music(bot))
