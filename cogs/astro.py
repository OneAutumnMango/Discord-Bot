import math
from datetime import datetime
import pytz
import discord
from discord import app_commands
from discord.ext import commands

from weather.weather import Weather
from tides.tides import predict_tide
from celestialtracker import CelestialTracker, SunArcTimer
from discordBot import timestamp, create_embed, create_ws_embed, moon_info


class Astro(commands.Cog):
    """Astronomy related slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sunset", description="Show today's sunset time in UTC.")
    async def sunset(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Sunset at {timestamp(Weather().sunset())}')

    @app_commands.command(name="weather", description="Get the current weather forecast.")
    async def weather(self, interaction: discord.Interaction):
        forecast = Weather().weather_now()
        temp = forecast["temperature"]
        temp_margin = forecast["temp_margin"]
        feels_like = forecast["feels_like"]
        weather_desc = forecast["weather"]
        wind_speed = forecast["wind_speed"]
        cloud_cover = forecast["cloud_cover"]

        embed = create_embed(f"🌤️ Weather Forecast")
        embed.add_field(
            name=f"Dun Laoghaire",
            value=(
                f"Temperature: `{temp:.2f}±{temp_margin:.2f} °C` (feels like `{feels_like:.2f} °C`)\n"
                f"Weather: `{weather_desc}`\n"
                f"Wind Speed: `{wind_speed:.2f} m/s`\n"
                f"Cloud Cover: `{cloud_cover}%`"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tide", description="Get the current tide prediction for Dun Laoghaire.")
    async def tide(self, interaction: discord.Interaction):
        now = datetime.now(pytz.utc)
        await interaction.response.send_message(f"`{predict_tide(now)[0]:.2f}m` @ {timestamp(now)}")

    @app_commands.command(name="moon", description="Get the current moon position and size.")
    async def moon(self, interaction: discord.Interaction):
        alt, az, perc, rise_set_str, phase, phase_name, illum = moon_info()
        embed = create_embed(f"🌙 Moon Info")
        embed.add_field(
            name=f"Details",
            value=(
                f"Altitude: `{alt:.1f}°`\n"
                f"Azimuth: `{az:.1f}°`\n"
                f"%size of Avg.: `{perc:.1f}%`\n"
                f"{rise_set_str}\n"
                f"Phase: {phase_name} (`{phase:.1f}°`)\n"
                f"Illumination `{illum*100:.1f}%`"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sun", description="Get the current sun position in the sky.")
    async def sun(self, interaction: discord.Interaction):
        alt, az = CelestialTracker().sun_at()
        await interaction.response.send_message(f"Sun Alt: `{alt:.1f}°`, Az: `{az:.1f}°`")

    @app_commands.command(name="ws", description="Show tide, weather and moon near sunset.")
    async def ws(self, interaction: discord.Interaction):
        await interaction.response.defer()  # avoid timeout
        await interaction.followup.send(embed=create_ws_embed())

    @app_commands.command(name="horizon", description="Calculate distance to the horizon from height.")
    @app_commands.describe(height="Your eye level or viewpoint height in meters.")
    async def horizon(self, interaction: discord.Interaction, height: float):
        if height < 0:
            await interaction.response.send_message("Height must be non-negative.", ephemeral=True)
            return

        r = 6356752.3  # Earth radius in meters
        distance_m = math.sqrt(2 * r * height + height ** 2)
        distance_km = distance_m / 1000

        await interaction.response.send_message(
            f"At a height of `{height:.2f}m`, the horizon is approximately `{distance_km:.2f}km` away."
        )

    @app_commands.command(name="handtime", description="Time for the sun to move one handwidth.")
    async def handtime(self, interaction: discord.Interaction):
        t, _ = SunArcTimer().minutes_per_hand_near_sunset()
        await interaction.response.send_message(f"`{t:.1f}` minutes per handwidth (`7.149°`)")

async def setup(bot: commands.Bot):
    await bot.add_cog(Astro(bot))
