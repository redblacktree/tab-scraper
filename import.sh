#!/usr/bin/env bash

source /home/webquest/venvs/racingcp/bin/activate
ls -1 /home/uploader/json-data/*.json | xargs --no-run-if-empty -n1 python /home/uploader/racingcp-test/manage.py scrape --import-json
rm /home/uploader/json-data/*.json