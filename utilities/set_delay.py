import os
import sys
import argparse
import datetime

# This file is just a convenience to automatically write out the DELAY
# file with the proper datetime expiration string as the body.

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CUR_DIR, os.pardir))

parser = argparse.ArgumentParser()
parser.add_argument('--hours', help='# of hours to pause job execution', type=int, required=True)

args = vars(parser.parse_args())

# Calculate what the datetime object will be by adding the current time
# and the number of hours to delay. This will be the body of the DELAY file.
future_time = datetime.datetime.now() + datetime.timedelta(hours=args['hours'])

# Write out the DELAY file and make the body the expiration time.
f = open(os.path.join(PARENT_DIR, 'DELAY'), 'w')
f.write(future_time.strftime('%Y-%m-%d %H:%M'))
f.close()
