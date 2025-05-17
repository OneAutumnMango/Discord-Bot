import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import pytz

load_dotenv()
API_KEY = os.getenv("OPENWEATHERMAP")

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/"

IRELAND_TZ = pytz.timezone("Europe/Dublin")


class Weather:
    def __init__(self):
        self.lat = 53.29395
        self.lon = -6.13586
        self._recent_weather = None
        self._recent_forecast = None
        self._weather_cache_file = "weather.json"
        self._forecast_cache_file = "weather.json"

    def _grab_weather(self):
        params = {
            "lat": self.lat,
            "lon": self.lon,
            "appid": API_KEY,
            "units": "metric"
        }

        response = requests.get(OPENWEATHER_URL+"weather", params=params, timeout=10)

        if response.status_code != 200:
            print(f"⚠️ API request failed (status {response.status_code}): {response.text}")
            self._load_cached_weather()
            return

        self._recent_weather = response.json()

        with open(self._weather_cache_file, "w") as f:
            json.dump(self._recent_weather, f)

    def _grab_forecast(self):
        params = {
            "lat": self.lat,
            "lon": self.lon,
            "appid": API_KEY,
            "units": "metric"
        }
        response = requests.get(OPENWEATHER_URL+"forecast", params=params, timeout=10)

        if response.status_code != 200:
            print(f"⚠️ API request failed (status {response.status_code}): {response.text}")
            self._load_cached_forecast()
            return
        
        self._recent_forecast = response.json()

        with open(self._forecast_cache_file, "w") as f:
            json.dump(self._recent_forecast, f)

    def weather_at(self, target_dt) -> tuple[datetime, str]:
        self._grab_forecast()
        target_dt_utc = target_dt.astimezone(timezone.utc)

        closest_entry = min(
            self._recent_forecast["list"],
            key=lambda x: abs(datetime.fromtimestamp(x["dt"], tz=timezone.utc) - target_dt_utc)
        )

        dt = datetime.fromtimestamp(closest_entry["dt"], tz=IRELAND_TZ)
        temp = closest_entry["main"]["temp"]    
        temp_max = closest_entry["main"]["temp_max"]
        temp_min = closest_entry["main"]["temp_min"]
        feels_like = closest_entry["main"]["feels_like"]
        desc = closest_entry["weather"][0]["description"]
        wind = closest_entry["wind"]["speed"]
        clouds = closest_entry["clouds"]["all"]

        # temp_str = f"{temp}±{(temp_max - temp_min):.1f}"

        forecast_dict = {
            "temperature": temp,
            "temp_margin": temp_max - temp_min,
            "feels_like": feels_like,
            "weather": desc,
            "wind_speed": wind,
            "cloud_cover": clouds
        }

        return dt, forecast_dict

        # return dt, (
        #     f"Temperature: {temp_str} °C, fl. {feels_like} °C\n"
        #     f"Weather: {desc}\n"
        #     f"Wind Speed: {wind} m/s\n"
        #     f"Cloud Cover: {clouds}%"
        # )
    
    def weather_now(self):
        self._grab_weather()

        temp = self._recent_weather['main']['temp']
        temp_max = self._recent_weather['main']['temp_max']
        temp_min = self._recent_weather['main']['temp_min']
        feels_like = self._recent_weather['main']['feels_like']
        desc = self._recent_weather['weather'][0]['description']
        wind = self._recent_weather['wind']['speed']
        clouds = self._recent_weather['clouds']['all']

        temp_str = f"{temp}±{(temp_max - temp_min):.1f}"

        forecast_dict = {
            "temperature": temp,
            "temp_margin": temp_max - temp_min,
            "feels_like": feels_like,
            "weather": desc,
            "wind_speed": wind,
            "cloud_cover": clouds
        }

        return forecast_dict

        # return (
        #     f"Temperature: {temp_str} °C, fl. {feels_like} °C\n"
        #     f"Weather: {desc}\n"
        #     f"Wind Speed: {wind} m/s\n"
        #     f"Cloud Cover: {clouds}%"
        # )

    def _load_cached_weather(self):
        if os.path.exists(self._weather_cache_file):
            with open(self._weather_cache_file, "r") as f:
                self._recent_weather = json.load(f)
            print("✅ Loaded weather from cache.")
        else:
            raise RuntimeError("No cached weather available.")
    
    def _load_cached_forecast(self):
        if os.path.exists(self._forecast_cache_file):
            with open(self._forecast_cache_file, "r") as f:
                self._recent_forecast = json.load(f)
            print("✅ Loaded forecast from cache.")
        else:
            raise RuntimeError("No cached forecast available.")

    def sunset(self):
        if self._recent_weather is None: self._grab_weather()
        return datetime.fromtimestamp(self._recent_weather["sys"]["sunset"], tz=IRELAND_TZ)
    

# Run
if __name__ == "__main__":
    weather = Weather()
    print(weather.weather_now())

    sunset = weather.sunset()
    print(f"\n🌅 Sunset at: {sunset}")

    print(weather.weather_at(sunset))

