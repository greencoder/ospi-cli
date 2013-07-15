import os
import sys
import stat
import time

from opensprinkler import OpenSprinkler

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CUR_DIR, os.pardir))

# Look in the main directory for any files that end in .pid. The name of 
# the file represents the pid of any running Sprinkler programs
pid_files = [f for f in os.listdir(PARENT_DIR) if f.endswith('.pid')]

needs_cleanup = False
old_pid_files = []

# Look through any pid files we found and see if they are older than 30 
# minutes. If they are, we'll flag that we need to run some cleanup.
for file_name in pid_files:
    file_path = os.path.join(CUR_DIR, file_name)
    file_age_min = int(time.time() - os.stat(file_path)[stat.ST_MTIME])/60
    if file_age_min > 35:
        needs_cleanup = True
        old_pid_files.append(file_path)

# If we found any old files, we need to delete the file and turn the system off
# in case it's errantly running.
if not needs_cleanup:
    sys.exit()

sprinkler = OpenSprinkler()
sprinkler.cleanup()

# Any old files we found should be removed now that we've finished our 
# housekeeping.
for old_file in old_pid_files:
    print "Deleting File: %s" % old_file
    os.remove(old_file)
