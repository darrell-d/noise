import json
import re


REGION = "region"
CITY = "city"
FULL = "full"
UNKNOWN_LOCATION = "Lost in the world"
COORDINATES = re.compile(r"^\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*$")
NULL_ISLAND_EPSILON = 0.0001


def normalize_coordinates(value):
    """Return canonical coordinates, rejecting invalid fixes and Null Island."""
    if not isinstance(value, str) or not COORDINATES.match(value):
        return ""

    latitude_text, longitude_text = value.split(",", 1)
    try:
        latitude = float(latitude_text)
        longitude = float(longitude_text)
    except ValueError:
        return ""

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return ""
    if abs(latitude) < NULL_ISLAND_EPSILON and abs(longitude) < NULL_ISLAND_EPSILON:
        return ""
    return f"{latitude:.6f},{longitude:.6f}"


def location_precision_for_user(user):
    if user and user.is_authenticated and user.is_active:
        if user.is_staff or user.is_superuser:
            return FULL
        return CITY
    return REGION


def _location_payload(value):
    if not value:
        return None
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _component(details, component_types, short=False):
    key = "short_name" if short else "long_name"
    for result in details:
        for component in result.get("address_components") or []:
            if set(component.get("types") or []).intersection(component_types):
                value = component.get(key)
                if short and len(str(value or "").strip()) < 2:
                    value = component.get("long_name")
                return value or component.get("long_name")
    return None


def _formatted_result(details, result_types):
    for result_type in result_types:
        for result in details:
            types = set(result.get("types") or [])
            if result_type in types and "plus_code" not in types:
                return result.get("formatted_address")
    return None


def _join_location(*parts):
    return ", ".join(str(part).strip() for part in parts if str(part or "").strip())


def _region_from_details(details):
    region = _component(details, {"administrative_area_level_1"}, short=True)
    country = _component(details, {"country"}, short=True)
    if region or country:
        return _join_location(region, country)
    return _formatted_result(details, ("administrative_area_level_1", "country"))


def _city_from_details(details):
    city = _component(
        details,
        {"locality", "postal_town", "administrative_area_level_2"},
    )
    region = _component(details, {"administrative_area_level_1"}, short=True)
    country = _component(details, {"country"}, short=True)
    if city or region or country:
        return _join_location(city, region, country)
    return _formatted_result(
        details,
        ("locality", "postal_town", "administrative_area_level_2"),
    )


def _full_from_details(details):
    return _formatted_result(
        details,
        (
            "street_address",
            "premise",
            "subpremise",
            "establishment",
            "point_of_interest",
            "route",
            "neighborhood",
            "sublocality",
            "locality",
            "administrative_area_level_1",
            "country",
        ),
    )


def _coarse_plain_text(value, precision):
    if COORDINATES.match(value):
        return UNKNOWN_LOCATION

    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return UNKNOWN_LOCATION
    if precision == REGION:
        if len(parts) >= 2 and re.fullmatch(r"[A-Z]{2,3}", parts[-2]):
            return _join_location(parts[-2], parts[-1])
        return parts[-1]
    if len(parts) >= 3 and re.fullmatch(r"[A-Z]{2,3}", parts[-2]):
        return _join_location(parts[-3], parts[-2], parts[-1])
    return _join_location(*parts[-2:])


def format_location(value, precision=FULL):
    if value in (None, ""):
        return UNKNOWN_LOCATION

    payload = _location_payload(value)
    if payload is None:
        text = str(value).strip()
        if COORDINATES.match(text) and not normalize_coordinates(text):
            return UNKNOWN_LOCATION
        return text if precision == FULL else _coarse_plain_text(text, precision)

    details = payload.get("details") or []
    raw_coords = payload.get("raw_coords")
    if raw_coords and COORDINATES.match(str(raw_coords)) and not normalize_coordinates(str(raw_coords)):
        return UNKNOWN_LOCATION
    if precision == REGION:
        return _region_from_details(details) or UNKNOWN_LOCATION
    if precision == CITY:
        return _city_from_details(details) or UNKNOWN_LOCATION
    return _full_from_details(details) or raw_coords or UNKNOWN_LOCATION


def location_for_user(value, user):
    return format_location(value, location_precision_for_user(user))
