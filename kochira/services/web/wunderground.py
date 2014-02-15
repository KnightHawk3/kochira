"""
Weather Underground forecast.

Get weather data from Weather Underground
"""

import requests

from urllib.parse import quote

from pydle.async import coroutine

from kochira import config
from kochira.service import Service, background, Config
from kochira.userdata import UserData

service = Service(__name__, __doc__)


@service.config
class Config(Config):
    api_key = config.Field(doc="Weather Underground API key.")


@service.command(r"weather(?: for (?P<where>.+))?", mention=True)
@background
@coroutine
def weather(client, target, origin, where=None):
    """
    Weather.

    Get the weather for a location.
    """
    config = service.config_for(client.bot, client.name, target)

    try:
        user_data = yield UserData.lookup(client, origin)
    except UserData.DoesNotExist:
        user_data = {}

    if where is None:
        if "location" not in user_data:
            client.message(target, "{origin}: I don't have location data for you.".format(
                origin=origin,
            ))
            return
        where = "{lat:.10},{lng:.10}".format(**user_data["location"])


    r = requests.get("http://api.wunderground.com/api/{api_key}/conditions/q/{where}.json".format(
        api_key=config.api_key,
        where=quote(where)
    )).json()

    if "error" in r:
        client.message(target, "{origin}: Sorry, there was an error: {type}: {description}".format(
            origin=origin,
            **r["error"]
        ))
        return

    if "current_observation" not in r:
        client.message(target, "{origin}: Couldn't find weather for \"{where}\".".format(
            origin=origin,
            where=where
        ))
        return

    observation = r["current_observation"]

    place = observation["display_location"]["full"]

    if observation["display_location"]["country"].upper() == "US":
        def _unitize(nonus, us):
            return us
    else:
        def _unitize(nonus, us):
            return nonus

    temp = observation["temp_" + _unitize("c", "f")]
    feelslike = observation["feelslike_" + _unitize("c", "f")]
    wind = observation["wind_" + _unitize("kph", "mph")]
    wind_dir = observation["wind_dir"]
    humidity = observation["relative_humidity"]
    precip = observation["precip_today_" + _unitize("metric", "in")]
    weather = observation["weather"]

    client.message(target, "{origin}: Today's weather for {place} is: {weather}, {temp} º{cf}, wind from {wind_dir} at {wind} {kphmph}, {humidity} humidity, {precip} {mmin} precipitation".format(
        origin=origin,
        place=place,
        weather=weather,
        temp=temp,
        cf=_unitize("C", "F"),
        wind_dir=wind_dir,
        wind=wind,
        kphmph=_unitize("km/h", "mph"),
        humidity=humidity,
        precip=precip,
        mmin=_unitize("mm", "in")
    ))