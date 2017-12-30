import os
import json
import logging.config

def setup_logging(path='/Users/Grignon/development/python/cabinpi/cabin_camera/logs/logging_config.json', default_level=logging.INFO):
    logging.config.dictConfig(json.load(open(path, 'rt')))

