import os
from dotenv import load_dotenv
from govee_py2.govee import GoveeClient
import time


def _get_client():
    load_dotenv()
    api_key = os.getenv('GOVEE_APIKEY')

    return GoveeClient(api_key)

def toggle(mode=None):
    client = _get_client()

    for d in client.devices:
        try:
            d.toggle(mode)
            d.set_brightness(100)
            time.sleep(0.5)
        except Exception as e:
            if "429" in str(e):
                time.sleep(5)
                print("rate limit exceeded")


def set_brightness(b=100):
    client = _get_client()

    for d in client.devices:
        try:
            d.set_brightness(100)
            time.sleep(0.5)
        except Exception as e:
            if "429" in str(e):
                time.sleep(5)
                print("rate limit exceeded")
