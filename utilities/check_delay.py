import os
import sys
import datetime

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CUR_DIR, os.pardir))

# The "delay" file is a file-based flag. If present in the directory 
# when the sprinkler program is run, the program will abort. The body 
# of the file is a datetime string that represents when the delay should 
# expire. Once expired, we want the file to be removed so that normal 
# operations can resume.

delay_file_path = os.path.join(PARENT_DIR, 'DELAY')

# If there is no DELAY file, abort.
if not os.path.exists(delay_file_path):
    sys.exit("DELAY file not present. Aborting.")

# Read in the DELAY file. The body contents should be the 
# expiration time of the delay.
f = open(delay_file_path, 'r')
data = f.read()
f.close()

# The contents of the file should be the datetime when the file expires
try:
    # Try to turn the body into a datetime object
    expiration = datetime.datetime.strptime(data, '%Y-%m-%d %H:%M')
    now = datetime.datetime.now()

    # If the expiration time is less than now (i.e. it has passed)
    # then go ahead and remove the file.
    if now >= expiration:
        print "Expiration has passed. Removing file."
        os.remove(delay_file_path)
    else:
        delta = (expiration - now)
        minutes = int(delta.seconds/60)
        if minutes > 60:
            print "Delay in effect for %.1f more hours." % float(minutes/60)
        else:
            print "Delay in effect for %d more minutes." % int(minutes)

except ValueError:
    # If we can't cast the value of the file into a date object, there is 
    # no sense keeping the file around. Deleate it.
    print "Could not read date in file. Removing file."
    os.remove(delay_file_path)
