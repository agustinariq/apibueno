"""app.services.location.local.py"""
import csv
from datetime import datetime

from asyncache import cached
from cachetools import TTLCache

from ...coordinates import Coordinates
from ...location import TimelinedLocation
from ...timeline import Timeline
from ...utils import countries
from ...utils import date as date_util
from . import LocationService


class LocalLocationService(LocationService):
    """
    Service for retrieving locations from local repository(https://github.com/facttic/apibueno).
    """

    async def get_all(self):
        # Get the locations.
        locations = await get_locations()
        return locations

    async def get(self, loc_id):  # pylint: disable=arguments-differ
        # Get location at the index equal to provided id.
        locations = await self.get_all()
        return locations[loc_id]


# ---------------------------------------------------------------


# Base DIR for fetching category.
BASE_DIR = (
    "app/data/"
)


@cached(cache=TTLCache(maxsize=1024, ttl=3600))
async def get_category(category):
    """
    Retrieves the data for the provided category. The data is cached for 1 hour.

    :returns: The data for category.
    :rtype: dict
    """

    # Adhere to category naming standard.
    category = category.lower()

    # DIR to get data from.
    dir = BASE_DIR + "time_series_%s.csv" % category

    # Open the file
    with open(dir, mode='r') as csv_file:
        # Parse the CSV.
        data = list(csv.DictReader(csv_file))

    # The normalized locations.
    locations = []

    for item in data:
        # Filter out all the dates.
        dates = dict(filter(lambda element: date_util.is_date(element[0]), item.items()))

        # Make location history from dates.
        history = {date: int(amount or 0) for date, amount in dates.items()}

        # Country for this location.
        country = item["Country/Region"]

        # Latest data insert value.
        latest = list(history.values())[-1]

        # Normalize the item and append to locations.
        locations.append(
            {
                # General info.
                "country": country,
                "country_code": countries.country_code(country),
                "province": item["Province/State"],
                # Coordinates.
                "coordinates": {"lat": item["Lat"], "long": item["Long"],},
                # History.
                "history": history,
                # Latest statistic.
                "latest": int(latest or 0),
            }
        )

    # Latest total.
    latest = sum(map(lambda location: location["latest"], locations))

    # Return the final data.
    return {
        "locations": locations,
        "latest": latest,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "source": "https://github.com/facttic/apibueno",
    }


@cached(cache=TTLCache(maxsize=1024, ttl=3600))
async def get_locations():
    """
    Retrieves the locations from the categories. The locations are cached for 1 hour.

    :returns: The locations.
    :rtype: List[Location]
    """
    # Get all of the data categories locations.
    confirmed = await get_category("confirmed")
    deaths = await get_category("deaths")
    # recovered = await get_category("recovered")

    locations_confirmed = confirmed["locations"]
    locations_deaths = deaths["locations"]
    # locations_recovered = recovered["locations"]

    # Final locations to return.
    locations = []

    # Go through locations.
    for index, location in enumerate(locations_confirmed):
        # Get the timelines.
        timelines = {
            "confirmed": locations_confirmed[index]["history"],
            "deaths": locations_deaths[index]["history"],
            # 'recovered' : locations_recovered[index]['history'],
        }

        # Grab coordinates.
        coordinates = location["coordinates"]

        # Create location (supporting timelines) and append.
        locations.append(
            TimelinedLocation(
                # General info.
                index,
                location["country"],
                location["province"],
                # Coordinates.
                Coordinates(coordinates["lat"], coordinates["long"]),
                # Last update.
                datetime.utcnow().isoformat() + "Z",
                # Timelines (parse dates as ISO).
                {
                    "confirmed": Timeline(
                        {
                            datetime.strptime(date, "%m/%d/%y").isoformat() + "Z": amount
                            for date, amount in timelines["confirmed"].items()
                        }
                    ),
                    "deaths": Timeline(
                        {
                            datetime.strptime(date, "%m/%d/%y").isoformat() + "Z": amount
                            for date, amount in timelines["deaths"].items()
                        }
                    ),
                    "recovered": Timeline({}),
                },
            )
        )

    # Finally, return the locations.
    return locations