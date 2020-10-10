#!/usr/bin/env bash

nordvpn connect nz71
source /root/tabscraper/env/bin/activate
echo "Retrieving today's upcoming races"
python /root/tabscraper/get_upcoming.py -vvv -d 0 -o /root/tabscraper/data/
echo "Retrieving tomorrow's upcoming races"
python /root/tabscraper/get_upcoming.py -vvv -d 1 -o /root/tabscraper/data/
echo "Retrieving the day after tomorrow's upcoming races"
python /root/tabscraper/get_upcoming.py -vvv -d 2 -o /root/tabscraper/data/
#echo "Retrieving the day after the day after tomorrow's upcoming races"
#python /root/tabscraper/get_upcoming.py -vvv -d 3 -o /root/tabscraper/data/
echo "Retrieving today's resulted races"
python /root/tabscraper/get_resulted.py -vvv -d 0 -o /root/tabscraper/data/
echo "Retrieving yesterdays's resulted races"
python /root/tabscraper/get_resulted.py -vvv -d 1 -o /root/tabscraper/data/
nordvpn d
scp /root/tabscraper/data/*.json racingcp:/home/uploader/json-data/
scp /root/tabscraper/data/*.json racingcp:/home/uploader/json-data-backup/
ssh racingcp bash -c "/home/uploader/import.sh"
rm /root/tabscraper/data/*