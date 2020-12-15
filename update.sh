#!/usr/bin/env bash

nordvpn connect nz71
source /root/tabscraper-v2/env/bin/activate
echo "Retrieving today's upcoming races"
python /root/tabscraper-v2/get_upcoming.py -vvv -d 0 -o /root/tabscraper-v2/data/ -r HORSE_RACING
python /root/tabscraper-v2/get_upcoming.py -vvv -d 0 -o /root/tabscraper-v2/data/ -r HARNESS_RACING
python /root/tabscraper-v2/get_upcoming.py -vvv -d 0 -o /root/tabscraper-v2/data/ -r GREYHOUNDS
echo "Retrieving tomorrow's upcoming races"
python /root/tabscraper-v2/get_upcoming.py -vvv -d 1 -o /root/tabscraper-v2/data/ -r HORSE_RACING
python /root/tabscraper-v2/get_upcoming.py -vvv -d 1 -o /root/tabscraper-v2/data/ -r HARNESS_RACING
python /root/tabscraper-v2/get_upcoming.py -vvv -d 1 -o /root/tabscraper-v2/data/ -r GREYHOUNDS
echo "Retrieving the day after tomorrow's upcoming races"
python /root/tabscraper-v2/get_upcoming.py -vvv -d 2 -o /root/tabscraper-v2/data/ -r HORSE_RACING
python /root/tabscraper-v2/get_upcoming.py -vvv -d 2 -o /root/tabscraper-v2/data/ -r HARNESS_RACING
python /root/tabscraper-v2/get_upcoming.py -vvv -d 2 -o /root/tabscraper-v2/data/ -r GREYHOUNDS
#echo "Retrieving the day after the day after tomorrow's upcoming races"
#python /root/tabscraper-v2/get_upcoming.py -vvv -d 3 -o /root/tabscraper-v2/data/
echo "Retrieving today's resulted races"
python /root/tabscraper-v2/get_resulted.py -vvv -d 0 -o /root/tabscraper-v2/data/ -r HORSE_RACING
python /root/tabscraper-v2/get_resulted.py -vvv -d 0 -o /root/tabscraper-v2/data/ -r HARNESS_RACING
python /root/tabscraper-v2/get_resulted.py -vvv -d 0 -o /root/tabscraper-v2/data/ -r GREYHOUNDS
echo "Retrieving yesterdays's resulted races"
python /root/tabscraper-v2/get_resulted.py -vvv -d 1 -o /root/tabscraper-v2/data/ -r HORSE_RACING
python /root/tabscraper-v2/get_resulted.py -vvv -d 1 -o /root/tabscraper-v2/data/ -r HARNESS_RACING
python /root/tabscraper-v2/get_resulted.py -vvv -d 1 -o /root/tabscraper-v2/data/ -r GREYHOUNDS
nordvpn d
scp /root/tabscraper-v2/data/*.json racingcp:/home/uploader/json-data-v2/
scp /root/tabscraper-v2/data/*.json racingcp:/home/uploader/json-data-backup-v2/
ssh racingcp bash -c "/home/uploader/import.sh"
rm /root/tabscraper-v2/data/*