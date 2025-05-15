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

if __name__ == "__main__":
    ct = CelestialTracker()
    print(ct.moon_angular_diameter_pct())
    print(ct.moon_rise_set())