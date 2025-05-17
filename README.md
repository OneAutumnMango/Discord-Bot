# Discord Bot

A Python-powered Discord bot built for fun and functionality. Includes astronomy, weather, tides, and classic games like Rock Paper Scissors.

## Setup

1. Clone the repo and install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the root directory with your Discord bot token:
   ```env
   TOKEN=your_discord_bot_token
   SERVER=discord_server_name
   OPENWEATHERMAP=openweathermap_free_apikey
   ```

> **Note:** This token should remain secret. Do not commit your `.env` file.

3. Run the bot:
   ```bash
   python bot.py
   ```

---

## Commands

### 🎮 Rock Paper Scissors

Play a quick game of rock, paper, scissors with the bot.

```bash
-rps [choice]
```

**Arguments:**
- `r`, `rock`: Choose rock  
- `p`, `paper`: Choose paper  
- `s`, `scissors`: Choose scissors  
- `score`, `stats`: Show your win/loss/draw record

**Example:**
```
-rps rock
-rps score
```

---

### 🌇 `sunset` or `s`

Displays today's sunset time.

```bash
-sunset
```

**Output:**
```
Sunset at 20:47
```

---

### 🌤️ `weather` or `w`

Returns the current weather forecast for Dún Laoghaire.

```bash
-weather
```

**Includes:**
- Temperature (with margin of error)
- Feels-like temperature
- Weather description
- Wind speed
- Cloud cover

---

### 🌊 `tide` or `t`

Displays the current tide prediction at Dún Laoghaire.

```bash
-tide
```

**Example Output:**
```
`0.92m` @ 14:12
```

---

### 🌙 `moon`

Displays the current Moon position and size percentage, along with rise/set times.

```bash
-moon
```

**Includes:**
- Altitude and azimuth
- Size compared to average
- Moonrise and moonset info

---

### ☀️ `sun`

Shows the Sun’s current altitude and azimuth (angle off north).

```bash
-sun
```

**Example Output:**
```
Sun Alt: 25.3°, Az: 180.1°
```

---

### 🌅 `ws`

Combined weather and tide summary around today’s sunset time.

```bash
-ws
```

---

### 🌍 `horizon` or `hori` or `h`

Calculates the distance to the horizon based on a given height (in meters).

```bash
-horizon [height]
```

**Example:**
```
-h 1.75
```

**Output:**
```
At a height of 1.75m, the horizon is approximately 4.72km away.
```

---

## Notes

- All time outputs use discord timestamps to account for timezone differences 
- Currently tuned for **Dún Laoghaire**, Ireland.
- This bot uses astronomy and weather libraries under the hood, plus Discord's command extensions.
