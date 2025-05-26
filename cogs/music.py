import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from discord_music_core.musicbot import MusicBot


class Music(commands.Cog):
    """Music related commands."""

    def __init__(self, bot):
        self.bot = bot

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     await self.bot.tree.sync()
    #     print(f'Bot is ready! Logged in as {self.bot.user}')

    async def _join_vc(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("You're not connected to a voice channel.", ephemeral=True)
            return None

        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is not None:
            if voice_client.channel != channel:
                await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()
        
        return voice_client



    @app_commands.command(name="join", description="Joins your voice channel")
    async def join(self, interaction: discord.Interaction):
        """
        Joins the voice channel that the user is currently in.

        If the bot is already connected to a voice channel in the same guild, it will move to the user's current channel.
        """

        await self._join_vc(interaction)

    @app_commands.command(name="leave", description="Stops playback and leaves the voice channel")
    async def leave(self, interaction: discord.Interaction):
        """
        Stops any music playback and disconnects the bot from the voice channel.
        """

        vc = interaction.guild.voice_client
        if vc is None:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
            return

        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.stop()
        await vc.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel.")

    @app_commands.command(name="play", description="Play a song from a YouTube URL or search query")
    @app_commands.describe(
        query="YouTube video URL or search query"
    )
    async def play(self, interaction: discord.Interaction, query: str):
        """
        Plays a song using a YouTube URL or a search query.

        :param str query: Either a direct YouTube video URL or a text search query (e.g., "lofi hip hop", "https://www.youtube.com/watch?v=dQw4w9WgXcQ").

        If the bot is not in a voice channel, it will automatically join the one you're in.
        The song will be added to the playback queue and start playing if nothing is currently playing.
        """

        await interaction.response.defer()  # avoid timeout

        vc = await self._join_vc(interaction)
        if vc is None:
            return

        if not hasattr(self.bot, "musicbot"):
            loop = asyncio.get_running_loop()
            self.bot.musicbot = MusicBot(vc, loop)
        else:
            if self.bot.musicbot.voice_client != vc:
                self.bot.musicbot.voice_client = vc

        title = await self.bot.musicbot.play(query)
        if title:
            await interaction.followup.send(f"Added to queue: {title}")
        else:
            await interaction.followup.send(f"No song matching '{query}' found.")

    @app_commands.command(name="skip", description="Skips the current song")
    async def skip(self, interaction: discord.Interaction):
        """
        Skips the currently playing song.
        """

        if not hasattr(self.bot, "musicbot"):
            await interaction.response.send_message("Music bot is not initialized.", ephemeral=True)
            return
        self.bot.musicbot.skip()
        await interaction.response.send_message("Skipped the current song.")

    @app_commands.command(name="nowplaying", description="Shows the current song playing")
    async def nowplaying(self, interaction: discord.Interaction):
        """
        Displays information about the currently playing song.
        """

        if not hasattr(self.bot, "musicbot"):
            await interaction.response.send_message("Music bot is not initialized.", ephemeral=True)
            return

        current = self.bot.musicbot.get_current()
        if current:
            await interaction.response.send_message(f"Currently playing: {current}")
        else:
            await interaction.response.send_message("No song is currently playing.")

    @app_commands.command(name="queue", description="Shows the songs in the queue")
    async def queue(self, interaction: discord.Interaction):
        """
        Lists all the songs currently in the queue.
        """
        
        if not hasattr(self.bot, "musicbot"):
            await interaction.response.send_message("Music bot is not initialized.", ephemeral=True)
            return

        queue_items = self.bot.musicbot.get_queue()
        if not queue_items:
            await interaction.response.send_message("The queue is empty.")
            return

        titles = [title for _, title in queue_items]
        await interaction.response.send_message("Queue:\n" + "\n".join(f"- `{title}`" for title in titles))

    @app_commands.command(name="stop", description="Stops playback and clears the queue")
    async def stop(self, interaction: discord.Interaction):
        """
        Stops the music playback and clears the entire queue.
        """

        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.stop()
            await interaction.response.send_message("Playback stopped and queue cleared.")
        else:
            await interaction.response.send_message("Music bot is not initialized.", ephemeral=True)

    @app_commands.command(name="pause", description="Pauses playback")
    async def pause(self, interaction: discord.Interaction):
        """
        Pauses the currently playing song.

        Playback can be resumed later using the /resume command.
        """

        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.pause()
            await interaction.response.send_message("Playback paused.")
        else:
            await interaction.response.send_message("Music bot is not initialized.", ephemeral=True)

    @app_commands.command(name="resume", description="Resumes playback")
    async def resume(self, interaction: discord.Interaction):
        """
        Resumes playback of a paused song.
        """

        if hasattr(self.bot, "musicbot"):
            self.bot.musicbot.resume()
            await interaction.response.send_message("Playback resumed.")
        else:
            await interaction.response.send_message("Music bot is not initialized.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))
