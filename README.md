TAB Scraper
===========
TAB Scraper provides two python scripts for extracting data from [TAB](https://www.tab.co.nz). `get_upcoming.py` and 
`get_resulted.py`. These commands are combined with some environment-specific commands in `update.sh` which handle
connecting to a VPN, running the scripts with several different parameters, uploading the results to another server
and importing those results on that server by running `import.sh` there.

Installation
------------
Install Python 3 and pip. Create a virtualenv and activate it. Install requirements with `pip -r requirements.txt`


### Command-Line Options for the scraping scripts:

#### get_upcoming.py

    usage: get_upcoming.py [-h] [-o OUTPUT_DIR] [-d OFFSET_DAYS] [-s] [-v]
                           [--version]
    
    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT_DIR, --output_dir OUTPUT_DIR
      -d OFFSET_DAYS, --offset_days OFFSET_DAYS
                            Days in the future to get race info for. 0=today e.g.
                            1=tomorrow (defaults to today)
      -s, --save-source-data
                            Save source data files for debugging (warning: large
                            files -- 3-6MB each)
      -v, --verbose         Verbosity (-v, -vv, etc)
      --version             show program's version number and exit

#### get_resulted.py

    usage: get_resulted.py [-h] [-o OUTPUT_DIR] [-d OFFSET_DAYS] [-s] [-v]
                           [--version]
    
    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT_DIR, --output_dir OUTPUT_DIR
      -d OFFSET_DAYS, --offset_days OFFSET_DAYS
                            Days in the past to get results for. e.g. 1=yesterday,
                            0=today (defaults to today
      -s, --save-source-data
                            Save source data files for debugging (warning: large
                            files -- 3-6MB each)
      -v, --verbose         Verbosity (-v, -vv, etc)
      --version             show program's version number and exit
      
  
Data Maps
---------
In both scripts there are data maps at the top of the file. The left side of these dictionaries
is the name of the key to write in the output, while the right side is a dot-notated path in
the JSON input to retrieve the value from. Note the integers in the input. This will return
list indexes, similar to Django's template syntax. 

**Note: They do not handle nested data structures.**  

Where nested data structures are added to the output, the hierarchy is defined within the scraping
functions, but another flat data map may be used to extract the correct data for each sub-item.

Formatting Dictionaries
-----------------------
Similar to the data maps, there are formatting dictionaries as well. These apply a function to the
named key in each set of data and write the result. These are currently all lambdas, but any
callable would work. 

Debugging
---------
There are a couple of tools to help with debugging:

1. There are logs available in /tmp/
2. The `-s` option will write the JSON file the script is parsing to the output directory.
   These are in the form `[event_id].json`. The `event_id` is at the top of every output
   file.
   
Imitating a User/Rate-limiting
------------------------------
The scripts attempt to imitate a user by including headers typical of an actual browser,
and by retrieving and using a Cloudfare user cookie on each run. The script also pauses
for 0.5 seconds between each request to avoid flooding the server.