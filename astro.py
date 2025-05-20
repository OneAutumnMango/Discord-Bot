from datetime import datetime, timezone, timedelta
from skyfield.api import load, wgs84
from skyfield import almanac
from math import degrees, atan2

class CelestialTracker:
    def __init__(self, latitude: float = 53.29395, longitude: float = -6.13586, elevation_m: float = 0):
        self.latitude = latitude
        self.longitude = longitude
        self.elevation_m = elevation_m
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        self.sun = self.eph['sun']
        self.moon = self.eph['moon']

    def _get_observer(self):
        return self.earth + self._get_topos()
    
    def _get_topos(self):
        return wgs84.latlon(
            latitude_degrees=self.latitude,
            longitude_degrees=self.longitude,
            elevation_m=self.elevation_m
        )

    def generic_alt_az(self, body, dt: datetime=None):
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (e.g., in UTC)")

        t = self.ts.from_datetime(dt)
        observer = self._get_observer()
        astrometric = observer.at(t).observe(body).apparent()
        alt, az, _ = astrometric.altaz()
        return alt.degrees, az.degrees

    def sun_at(self, dt: datetime=None):
        return self.generic_alt_az(self.sun, dt)

    def moon_at(self, dt: datetime=None):
        return self.generic_alt_az(self.moon, dt)

    def moon_angular_diameter_pct(self, dt: datetime = None):
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (e.g., in UTC)")
        
        MOON_RADIUS_KM = 1737.4
        MOON_MEAN_DIAMETER_DEG = 0.5181  # in degrees

        t = self.ts.from_datetime(dt)
        observer = self._get_observer()
        astrometric = observer.at(t).observe(self.moon).apparent()
        _, _, distance = astrometric.altaz()
        distance_km = distance.km

        # Angular diameter in degrees
        diameter_deg = degrees(2 * atan2(MOON_RADIUS_KM, distance_km))
        percent_of_average = (diameter_deg / MOON_MEAN_DIAMETER_DEG) * 100
        return diameter_deg, percent_of_average
    
    def moon_rise_set(self, dt: datetime = None, horizon_degrees: float = 0.0):
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware (e.g., in UTC)")

        ts = self.ts
        eph = self.eph

        # Define time window: from dt to dt + 24 hours
        t0 = ts.from_datetime(dt)
        t1 = ts.from_datetime(dt + timedelta(days=1))

        f = almanac.risings_and_settings(eph, eph['moon'], self._get_topos(), horizon_degrees=horizon_degrees)

        times, events = almanac.find_discrete(t0, t1, f)

        rise_time = None
        set_time = None

        # events: 0 = set, 1 = rise
        for t, event in zip(times, events):
            if event == 1 and rise_time is None and t.utc_datetime() > dt:
                rise_time = t.utc_datetime()
            elif event == 0 and set_time is None and t.utc_datetime() > dt:
                set_time = t.utc_datetime()
            if rise_time and set_time:
                break

        return rise_time, set_time

class SunArcTimer():
    def __init__(self, latitude: float = 53.29395, longitude: float = -6.13586, arc_deg: float = 7.149):
        self.latitude = latitude
        self.longitude = longitude
        self.arc_deg = arc_deg
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        self.sun = self.eph['sun']
        self.location = wgs84.latlon(latitude, longitude)

    def _get_altitude(self, t):
        astrometric = self.earth + self.location
        alt, _, _ = astrometric.at(t).observe(self.sun).apparent().altaz()
        return alt.degrees
    
    def _sunset_time(self):
        now = datetime.now(timezone.utc)
        t0 = self.ts.utc(now.year, now.month, now.day)
        t1 = self.ts.utc((now + timedelta(days=1)).year, 
                         (now + timedelta(days=1)).month, 
                         (now + timedelta(days=1)).day)

        f = almanac.sunrise_sunset(self.eph, self.location)
        times, events = almanac.find_discrete(t0, t1, f)

        for t, e in zip(times, events):
            if e == 0:  # 0 = sunset
                return t.utc_datetime()

        return None
    
    def find_time_of_altitude(self, target_alt, after_utc):
        """Find the UTC time when the Sun crosses down through target_alt (°)."""
        step_sec = 30
        now = after_utc
        prev_alt = self._get_altitude(self.ts.from_datetime(now))

        # Keep stepping until sunset or we find a crossing
        sunset = self._sunset_time()
        if not sunset:
            return None

        while now < sunset:
            future = now + timedelta(seconds=step_sec)
            alt = self._get_altitude(self.ts.from_datetime(future))
            print(f"checking at {future} -> {alt}")


            if prev_alt >= target_alt and alt <= target_alt:
                # Linear interpolation between time steps
                ratio = (prev_alt - target_alt) / (prev_alt - alt)
                crossing_time = now + timedelta(seconds=step_sec * ratio)
                return crossing_time

            now = future
            prev_alt = alt

        return None


    def minutes_per_hand_near_sunset(self, hands_above=2):
        now = datetime.now(timezone.utc)

        segments = []
        current_alt = self.arc_deg * hands_above

        time_at_current = self.find_time_of_altitude(current_alt, now)
        if not time_at_current:
            return None

        # Step down in hand-widths
        for h in range(hands_above, 0, -1):
            next_alt = self.arc_deg * (h - 1)
            time_at_next = self.find_time_of_altitude(next_alt, time_at_current + timedelta(seconds=10))
            if not time_at_next:
                return None

            delta_min = (time_at_next - time_at_current).total_seconds() / 60
            segments.append(delta_min)

            time_at_current = time_at_next  # move to next step

        average = sum(segments) / len(segments)

        return average, segments

    def time_until_sun_drops_arc(self, max_minutes=180, step_seconds=30):
        now = datetime.now(timezone.utc)
        t_now = self.ts.from_datetime(now)
        start_alt = self._get_altitude(t_now)

        if start_alt <= 0:
            return 0, start_alt  # Sun is below horizon

        # Check how long until Sun is arc_deg lower
        target_alt = start_alt - self.arc_deg
        if target_alt <= 0:
            target_alt = 0  # Don't go below horizon

        # Step forward until altitude is equal or lower
        for i in range(1, int((max_minutes * 60) / step_seconds)):
            future_time = now + timedelta(seconds=i * step_seconds)
            t_future = self.ts.from_datetime(future_time)
            alt = self._get_altitude(t_future)
            if alt <= target_alt:
                elapsed = (future_time - now).total_seconds() / 60
                return elapsed, start_alt

        return None, start_alt  # Didn't drop arc_deg in max_minutes

if __name__ == "__main__":
    # ct = CelestialTracker()
    # print(ct.moon_angular_diameter_pct())
    # print(ct.moon_rise_set())

    sat = SunArcTimer()
    print(sat.time_until_sun_drops_arc())
    print(sat.minutes_per_hand_near_sunset())