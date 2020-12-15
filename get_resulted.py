#!/usr/bin/env python3
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
from common import format_data, map_data, get_cloudfare_cookie, COMMON_HEADERS, RACE_TYPES

logfile("/tmp/get-resulted.log", maxBytes=int(1e6), backupCount=10)

POOL_CODES = {
    "WIN": "Win",
    "PLC": "Place",
    "TFA": "Trifecta",
    "QLA": "Quinella",
    "FT4": "First4",
    "TRB": "Treble",
    "QAD": "Quaddie",
    "DBL": "Double"
}
RESULTED_RACE_DATA_MAPPING = {
    "event_id": "id",
    "meeting number": "race.meetingNumber",
    "meeting place": "type.name",
    "race number": "raceNumber",
    "iso date": "startTime"
}
RESULTED_RACE_FORMATTING_RULES = {
    "meeting number": lambda x: f"M{x}",
    "iso date": lambda x: x.replace("Z", "+00:00"),
    "race number": lambda x: str(x),
    "type": lambda x: RACE_TYPES[x]
}
RESULTED_RACE_PRIZES_DATA_MAPPING = {
    "prize": "position",
    "horse number": "runnerNumber",
    "horse name": "name"
}
RESULTED_RACE_PRIZES_FORMATTING_RULES = {
    "prize": lambda x: f"{x}" + {1: 'st', 2: 'nd', 3: 'rd', 4: 'th'}.get(x)
}
RESULTED_RACE_EXOTIC_POOL_DIVIDEND_DATA_MAPPING = {
    "prize": "type",
    "runners": "legs.0.result",
    "dividend": "value"
}
RESULTED_RACE_EXOTIC_POOL_DIVIDEND_FORMATTING_RULES = {
    "prize": lambda x: POOL_CODES.get(x, x)
}
RESULTED_EVENT_URL = "https://content.tab.co.nz/content-service/api/v1/q/resulted-events?eventIds={event_ids}&includeChildMarkets=true&includePools=true&includeRace=true&includeRunners=true"
RESULTED_EVENT_LIST_URL = "https://content.tab.co.nz/content-service/api/v1/q/resulted-event-list?drilldownTagIds=18%2C19%2C38&relativeMeetingOffsetDays=-{offset_days}&includePools=true&includeRacingResults=true&includeRace=true"


def get_resulted_event_list(cloudfare_cookie, locations=None, offset_days=0, race_type="HORSE_RACING"):
    if locations is None:
        logger.warning('get_resulted_event_list: No locations specified. Event list will return no results.')
        locations = []
    event_list = requests.get(url=RESULTED_EVENT_LIST_URL.format(offset_days=offset_days),
                              headers=COMMON_HEADERS.update({'__cfduid': cloudfare_cookie}))
    event_list_json = event_list.json()
    events = event_list_json['data']['eventResults']
    return [x for x in events if "class" in x and "name" in x["class"]
            and x["class"]["name"] in locations
            and "category" in x and "code" in x["category"]
            and x["category"]["code"] == race_type]


def dereference_outcomes(event_info):
    def get_outcome(event_info, outcome_id):
        for market in event_info["markets"]:
            outcome = next((x for x in market["outcomes"] if x["id"] == outcome_id), None)
            if outcome:
                return outcome
        return None
    for pool in event_info["pools"]:
        for dividend in pool.get("dividends", []):
            for leg in dividend.get("legs"):
                for i, outcome in enumerate(leg["outcomes"]):
                    leg["outcomes"][i] = get_outcome(event_info, outcome["id"])


def get_prize(event_info, position):
    win_price = ""
    place_price = ""
    if position == 1:
        win_pool = next((x for x in event_info["pools"] if x["type"] == "WIN"), None)
        if win_pool is None:
            logger.warning(f"No 'WIN' pool found, cannot return WIN prizes for event id {event_info['id']}")
        win_dividend = next((x for x in win_pool["dividends"] if x["type"] == "WIN"), None)
        if win_dividend is None:
            logger.warning(f"No 'WIN' dividend found in WIN pool, cannot return WIN prizes "
                           f"for event id {event_info['id']}")
        prices = win_dividend["legs"][0]["outcomes"][0]["prices"]
        logger.debug(json.dumps(win_dividend, indent=4))
        logger.debug(json.dumps(prices, indent=4))
        win_price_record = next((x for x in prices if x["priceType"] == "WIN_POOL"), None)
        if win_price_record is not None:
            win_price = win_price_record["decimal"]
        place_price_record = next((x for x in prices if x["priceType"] == "PLACE_POOL"), None)
        if place_price_record is not None:
            place_price = place_price_record["decimal"]
    else:
        place_pool = next((x for x in event_info["pools"] if x["type"] == "PLC"), None)
        if place_pool is None:
            logger.warning(f"No 'PLC' pool found, cannot return PLC prizes for event id {event_info['id']}")
        for dividend in place_pool["dividends"]:
            outcomes = dividend["legs"][0]["outcomes"]
            outcome = next((x for x in outcomes if x["result"]["position"] == position), None)
            if outcome is not None:
                place_price_record = next((x for x in outcome["prices"] if x["priceType"] == "PLACE_POOL"), None)
                if place_price_record is not None:
                    place_price = place_price_record["decimal"]
                else:
                    logger.warning(f"Found place outcome, but not place price for position {position} "
                                   f"in event {event_info['id']}")
            else:
                logger.debug(f"Did not find place outcome for position {position}")
    return {
        "win": str(win_price),
        "place": str(place_price)
    }


def get_top_positions(event_info):
    try:
        final_positions = event_info['result']['finalPositions']
    except KeyError:
        logger.error("Cannot find result and finalPositions")
        return []
    records = [format_data(map_data(x, RESULTED_RACE_PRIZES_DATA_MAPPING), RESULTED_RACE_PRIZES_FORMATTING_RULES) for
               x in sorted(final_positions, key=lambda x: x["position"])]
    [x.update(get_prize(event_info, i+1)) for i, x in enumerate(records)]
    return records


def get_exotics(event_info):
    records = []
    exotic_pools = [x for x in event_info["pools"] if x["type"] != "PLC" and x["type"] != "WIN"]
    for pool in exotic_pools:
        dividends = pool.get("dividends", [])
        if len(dividends) > 0:
            dividend = dividends[0]
            record = map_data(dividend, RESULTED_RACE_EXOTIC_POOL_DIVIDEND_DATA_MAPPING)
            record = format_data(record, RESULTED_RACE_EXOTIC_POOL_DIVIDEND_FORMATTING_RULES)
            records.append(record)
    return records


def get_resulted_event(cloudfare_cookie, event_id, save_source=False, output_dir=".", race_type="HORSE_RACING"):
    event_info = requests.get(url=RESULTED_EVENT_URL.format(event_ids=event_id),
                              headers=COMMON_HEADERS.update({'__cfduid': cloudfare_cookie})).json()
    logger.debug(json.dumps(event_info, indent=4))
    if save_source:
        filename = os.path.join(output_dir, f"{event_id}-results.json")
        with open(filename, "w") as debugfile:
            json.dump(event_info, debugfile, indent=4)
    event_info = event_info['data']['eventResults'][0]
    dereference_outcomes(event_info)
    mapped_event_info = map_data(event_info, mapping=RESULTED_RACE_DATA_MAPPING)
    mapped_event_info['type'] = race_type
    format_data(mapped_event_info, RESULTED_RACE_FORMATTING_RULES)
    mapped_event_info['groups'] = [{"name": "prizes", "records": get_top_positions(event_info)},
                                   {"name": "exotics", "records": get_exotics(event_info)}]
    return mapped_event_info


def main(args):
    loglevel((5 - args.verbose) * 10)  # -v for error+critical, up to -vvvv for debug+

    cloudfare_cookie = get_cloudfare_cookie()
    os.makedirs(args.output_dir, exist_ok=True)
    locations = ["New Zealand", "Australia"]
    resulted_events = get_resulted_event_list(cloudfare_cookie, locations, args.offset_days, args.race_type)
    event_ids = [x["id"] for x in resulted_events]
    logger.info("Found {n} events, with IDs {ids}".format(n=len(resulted_events),
                                                          ids=event_ids))
    for i, event_id in enumerate(event_ids):
        time.sleep(0.5)  # Be a good citizen - avoid throttling by limiting request frequency
        event_info = [get_resulted_event(cloudfare_cookie, event_id,
                                         save_source=args.save_source,
                                         output_dir=args.output_dir,
                                         race_type=args.race_type)]
        filename = f"{RACE_TYPES[args.race_type].lower()}-results-{event_info[0]['meeting number']}-"\
                   f"{event_info[0]['meeting place'].replace(' ', '_')}-R{event_info[0]['race number']}.json"
        filename = os.path.join(args.output_dir, filename)
        with open(filename, "w") as outfile:
            logger.info(f"Result {i + 1} of {len(event_ids)}. Writing file {filename}.")
            json.dump(event_info, outfile, indent=4)


if __name__ == "__main__":
    """ This is executed when run from the command line """
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output_dir", action="store", dest="output_dir", default="resulted")
    parser.add_argument("-d", "--offset_days", action="store", dest="offset_days", default="0",
                        help="Days in the past to get results for. e.g. 1=yesterday, 0=today (defaults to today")
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
