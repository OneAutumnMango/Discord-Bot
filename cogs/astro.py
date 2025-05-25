import math
from datetime import datetime
import pytz
from discord.ext import commands

from weather.weather import Weather
from tides.tides import predict_tide
from celestialtracker import CelestialTracker, SunArcTimer
from discordBot import timestamp, create_embed, create_ws_embed, moon_info


class Astro(commands.Cog):
    """Astronomy related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['s'], help="Shows today's sunset time in UTC.")
    async def sunset(self, ctx):
        await ctx.send(f'Sunset at {timestamp(Weather().sunset())}')

    @commands.command(aliases=['w'], help='Gets the current weather forecast.')
    async def weather(self, ctx):
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
        await ctx.send(embed=embed)

    @commands.command(aliases=['t'], help='Gets the current DL tide prediction.')
    async def tide(self, ctx):
        now = datetime.now(pytz.utc)
        await ctx.send(f"`{predict_tide(now)[0]:.2f}m` @ {timestamp(now)}")

    @commands.command(help="Gets the altitude and azimuth (angle off north) of the Moon.")
    async def moon(self, ctx):
        alt, az, perc, rise_set_str = moon_info()
        embed = create_embed(f"🌙 Moon Info")
        embed.add_field(
            name=f"Details",
            value=(
                f"Altitude: `{alt:.1f}°`\n"
                f"Azimuth: `{az:.1f}°`\n"
                f"%size of Avg.: `{perc:.1f}%`\n"
                f"{rise_set_str}"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(help="Gets the altitude and azimuth (angle off north) of the Sun.")
    async def sun(self, ctx):
        alt, az = CelestialTracker().sun_at()
        await ctx.send(f"Sun Alt: `{alt:.1f}°`, Az: `{az:.1f}°`")

    @commands.command(help="Tide and weather around today's sunset.")
    async def ws(self, ctx):
        await ctx.send(embed=create_ws_embed())

    @commands.command(aliases=['hori', 'h'], help="Calculates the distance to the horizon from a given height.")
    async def horizon(self, ctx, height: float):
        if height < 0:
            await ctx.send("Height must be non-negative.")
            return

        r = 6356752.3  # Earth radius in meters
        distance_m = math.sqrt(2*r*height + height**2)
        distance_km = distance_m / 1000

        await ctx.send(
            f"At a height of `{height:.2f}m`, the horizon is approximately `{distance_km:.2f}km` away."
        )

    @commands.command(help="Time in minutes for the sun to travel one handwidth. (avg of last 2 handwidths)")
    async def handtime(self, ctx):
        t, _ = SunArcTimer().minutes_per_hand_near_sunset()
        await ctx.send(f"`{t:.1f}` minutes per handwidth (`7.149°`)")

async def setup(bot):
    await bot.add_cog(Astro(bot))
