import json
import os
import googlemaps
from dotenv import load_dotenv
from django.conf import settings
from googlemaps.exceptions import ApiError
load_dotenv()

def is_json(input, return_json=False):
    try:
        json_object = json.loads(input)
    except Exception as e:
        return False
    if return_json:
        return json_object
    else:
        return True


def get_coord_data(coords):
    google_maps_key = getattr(settings, 'GOOGLE_MAPS_KEY', '') or os.getenv('GOOGLE_MAPS_KEY')
    if not google_maps_key:
        return []
    try:
        gmaps = googlemaps.Client(key=google_maps_key)
        return gmaps.reverse_geocode(tuple(coords.split(',')))
    except (ApiError, ValueError, OSError):
        return []
