#! /usr/bin/env python

# Getting GEO information from Nginx access.log by IP's.
# Alexey Nizhegolenko 2018

import os
import re
import sys
import time
import pygeoip
import Geohash
import configparser
from influxdb import InfluxDBClient


def logparse(LOGPATH, INFLUXHOST, INFLUXPORT, INFLUXDBDB, INFLUXUSER, INFLUXUSERPASS, MEASUREMENT): # NOQA
    # Preparing variables and params
    IPS = {}
    COUNT = {}
    GEOHASH = {}
    CLIENT = InfluxDBClient(host=INFLUXHOST, port=INFLUXPORT,
                            username=INFLUXUSER, password=INFLUXUSERPASS, database=INFLUXDBDB) # NOQA
    GETIP = r"^(?P<remote_host>[0-9]{,3}\.[0-9]{,3}\.[0-9]{,3}\.[0-9]{,3})"
    GI = pygeoip.GeoIP('GeoLiteCity.dat', pygeoip.const.MEMORY_CACHE)

    # Main loop to parse access.log file in tailf style with sending metrcs
    with open(LOGPATH, "r") as FILE:
        STR_RESULTS = os.stat(LOGPATH)
        ST_SIZE = STR_RESULTS[6]
        FILE.seek(ST_SIZE)
        while 1:
            METRICS = []
            WHERE = FILE.tell()
            LINE = FILE.readline()
            if not LINE:
                time.sleep(1)
                FILE.seek(WHERE)
            else:
                IP = re.search(GETIP, LINE).group(1)
                if IP:
                    INFO = GI.record_by_addr(IP)
                    if INFO is not None:
                        HASH = Geohash.encode(INFO['latitude'], INFO['longitude']) # NOQA
                        COUNT['count'] = 1
                        GEOHASH['geohash'] = HASH
                        GEOHASH['country_code'] = INFO['country_code']
                        IPS['tags'] = GEOHASH
                        IPS['fields'] = COUNT
                        IPS['measurement'] = MEASUREMENT
                        METRICS.append(IPS)

                        # Sending json data to InfluxDB
                        CLIENT.write_points(METRICS)


def main():
    # Preparing for reading config file
    PWD = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    CONFIG = configparser.ConfigParser()
    CONFIG.read('%s/settings.ini' % PWD)

    # Getting params from config
    LOGPATH = CONFIG.get('NGINX_LOG', 'logpath')
    INFLUXHOST = CONFIG.get('INFLUXDB', 'host')
    INFLUXPORT = CONFIG.get('INFLUXDB', 'port')
    INFLUXDBDB = CONFIG.get('INFLUXDB', 'database')
    INFLUXUSER = CONFIG.get('INFLUXDB', 'username')
    MEASUREMENT = CONFIG.get('INFLUXDB', 'measurement')
    INFLUXUSERPASS = CONFIG.get('INFLUXDB', 'password')

    # Parsing log file and sending metrics to Influxdb
    logparse(LOGPATH, INFLUXHOST, INFLUXPORT, INFLUXDBDB, INFLUXUSER, INFLUXUSERPASS, MEASUREMENT) # NOQA


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
