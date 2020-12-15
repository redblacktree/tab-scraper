#!/usr/bin/env python3
from copy import copy

__author__ = "Dustin Rasener"
__version__ = "0.1.0"
__license__ = "Proprietary"

import argparse
import json
import os
import time
from datetime import datetime
import requests
from logzero import logger, loglevel, logfile
try:
    from backports.datetime_fromisoformat import MonkeyPatch
    MonkeyPatch.patch_fromisoformat()
except ImportError:
    pass
from common import map_data, format_data, get_cloudfare_cookie, COMMON_HEADERS, RACE_TYPES

logfile("/tmp/get-upcoming.log", maxBytes=int(1e6), backupCount=10)

POOL_CODES = {
    "WIN": "Win",
    "PLC": "Place",
    "TFA": "Trifecta",
    "QLA": "Quinella"
}
UPCOMING_RACE_DATA_MAPPING = {
    "event_id": "id",
    "status": "status",
    "iso date": "meeting.date",
    "meeting number": "race.meetingNumber",
    "meeting place": "meeting.name",
    "race number": "raceNumber",
    "track": "race.track.name",
    "weather": "race.weather",
    "event time": "startTime",
    "event name": "race.name",
    "distance": "race.distance.distance",
    "prize pool": "race.stake"
}
UPCOMING_RACE_FORMAT_RULES = {
    "iso date": lambda x: x.replace("Z", "+00:00"),
    "meeting number": lambda x: f"M{x}",
    "track": lambda x: x[:10],
    "type": lambda x: RACE_TYPES[x]
}
UPCOMING_RACE_GROUP_MAPPINGS = {"COMMON": {
    "silk": "raceDetails.silkImageUri",
    "form": "lastFivePlacings",
    "position": "raceDetails.number",
    "name": "name",
    "trainer": "raceDetails.trainer.name",
    "scratched": "raceDetails.scratched"
}}
UPCOMING_RACE_GROUP_MAPPINGS["HORSE_RACING"] = copy(UPCOMING_RACE_GROUP_MAPPINGS["COMMON"])
UPCOMING_RACE_GROUP_MAPPINGS["HORSE_RACING"].update({
    "barrier": "raceDetails.barrier",
    "jockey": "raceDetails.jockey.name",
    "jockey weight": "raceDetails.handicap"
})
UPCOMING_RACE_GROUP_MAPPINGS["HARNESS_RACING"] = copy(UPCOMING_RACE_GROUP_MAPPINGS["COMMON"])
UPCOMING_RACE_GROUP_MAPPINGS["HARNESS_RACING"].update({
    "barrier": "raceDetails.barrier",
    "position": "raceDetails.barrier",
    "driver": "raceDetails.jockey.name",
    "handicap": "raceDetails.handicap"
})
UPCOMING_RACE_GROUP_FORMAT_RULES = {
    "handicap": lambda x: "" if x == "fr" else x
}
UPCOMING_RACE_GROUP_MAPPINGS["GREYHOUNDS"] = copy(UPCOMING_RACE_GROUP_MAPPINGS["COMMON"])
EVENT_LIST_URL = "https://content.tab.co.nz/content-service/api/v1/q/event-list?started=false&relativeMeetingOffsetDays={offset_days}&excludeResultedEvents=false&excludeExpiredMarkets=false&excludeSettledEvents=false&includeRace=true&includeMedia=true&includePools=true&drilldownTagIds=18%2C19%2C38"
EVENT_INFO_URL = "https://content.tab.co.nz/content-service/api/v1/q/events-by-ids?eventIds={event_ids}&includeChildMarkets=true&includeCollections=false&includePriceHistory=true&includeCommentary=false&includeIncidents=false&includeRace=true&includeMedia=true&includePools=true"


def get_upcoming_event_list(cloudfare_cookie, locations=None, offset_days=0, race_type="HORSE_RACING"):
    if locations is None:
        logger.warning('get_event_list: No locations specified. Event list will return no results.')
        locations = []
    event_list = requests.get(url=EVENT_LIST_URL.format(offset_days=offset_days),
                              headers=COMMON_HEADERS.update({'__cfduid': cloudfare_cookie}))
    event_list_json = event_list.json()
    events = event_list_json['data']['events']
    return [x for x in events if "class" in x and "name" in x["class"]
            and x["class"]["name"] in locations
            and "category" in x and "code" in x["category"]
            and x["category"]["code"] == race_type]


def get_odds(event_info, horse_name, price_type="WIN_POOL"):
    logger.debug(json.dumps(event_info, indent=4))
    win_market = next((x for x in event_info["markets"] if x["groupCode"] == "WINNER"), None)
    if win_market is None:
        logger.warning(f"No 'WINNER' market found, cannot return win odds for event id {event_info['id']}")
        return None
    outcome = next((x for x in win_market["outcomes"] if x["name"] == horse_name), None)
    if outcome is None:
        logger.warning(f"No 'outcome' found for {horse_name} in event id {event_info['id']}")
        return None
    win_pool = next((x for x in outcome["prices"] if x["priceType"] == price_type), None)
    if win_pool is None:
        logger.warning(f"No `{price_type}` price found for {horse_name} in event id {event_info['id']}")
        return None
    return str(win_pool["decimal"])


def get_event_info(cloudfare_cookie, event_id, save_source=False, output_dir=".", race_type="HORSE_RACING"):
    event_info = requests.get(url=EVENT_INFO_URL.format(event_ids=event_id),
                              headers=COMMON_HEADERS.update({'__cfduid': cloudfare_cookie})).json()
    if save_source:
        filename = os.path.join(output_dir, f"{event_id}-event.json")
        with open(filename, "w") as debugfile:
            json.dump(event_info, debugfile, indent=4)
    event_info = event_info['data']['events'][0]
    mapped_event_info = map_data(event_info, mapping=UPCOMING_RACE_DATA_MAPPING)
    mapped_event_info['type'] = race_type
    format_data(mapped_event_info, UPCOMING_RACE_FORMAT_RULES)
    mapped_event_info['group'] = []
    for runner in event_info['race']['runners']:
        runner_info = map_data(runner, mapping=UPCOMING_RACE_GROUP_MAPPINGS[race_type])
        win_odds = get_odds(event_info, runner["name"], price_type="LP")
        runner_info["indicative odds"] = win_odds
        tote_odds = get_odds(event_info, runner["name"], price_type="WIN_POOL")
        runner_info["tote_odds"] = tote_odds
        format_data(runner_info, UPCOMING_RACE_GROUP_FORMAT_RULES)
        if str(runner_info["scratched"]).lower() != "true":
            mapped_event_info['group'].append(runner_info)
    mapped_event_info['group'] = sorted(mapped_event_info['group'], key=lambda x: x['position'])
    return mapped_event_info


def main(args):
    loglevel((5 - args.verbose) * 10)  # -v for error+critical, up to -vvvv for debug+
    cloudfare_cookie = get_cloudfare_cookie()
    os.makedirs(args.output_dir, exist_ok=True)
    locations = ["New Zealand", "Australia"]
    upcoming_events = get_upcoming_event_list(cloudfare_cookie, locations, args.offset_days, args.race_type)
    event_ids = [x["id"] for x in upcoming_events]
    logger.info("Found {n} events, with IDs {ids}".format(n=len(upcoming_events),
                                                          ids=event_ids))
    for i, event_id in enumerate(event_ids):
        time.sleep(0.5)  # Be a good citizen - avoid throttling by limiting request frequency
        event_info = [get_event_info(cloudfare_cookie, event_id,
                                     save_source=args.save_source,
                                     output_dir=args.output_dir,
                                     race_type=args.race_type)]
        filename = f"{RACE_TYPES[args.race_type].lower()}-{event_info[0]['meeting number']}-" \
                   f"{event_info[0]['track'].replace(' ', '_')}" \
                   f"-R{event_info[0]['race number']}.json"
        filename = os.path.join(args.output_dir, filename)
        with open(filename, "w") as outfile:
            logger.info(f"Race {i+1} of {len(event_ids)}. Writing file {filename}.")
            json.dump(event_info, outfile, indent=4)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output_dir", action="store", dest="output_dir", default="./events")
    parser.add_argument("-d", "--offset_days", action="store", dest="offset_days", default="0",
                        help="Days in the future to get race info for. 0=today e.g. 1=tomorrow (defaults to today)")
    parser.add_argument("-s", "--save-source-data", action="store_true", dest="save_source", default=False,
                        help="Save source data files for debugging (warning: large files -- 3-6MB each)")
    parser.add_argument("-r", "--race-type", action="store", dest="race_type", default="HORSE_RACING",
                        help="Possible values: HORSE_RACING, HARNESS_RACING, GREYHOUNDS (defaults to HORSE_RACING)")

    # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbosity (-v, -vv, etc)")

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    args = parser.parse_args()
    main(args)
