import os
import sys
import time
import atexit
import datetime
import argparse

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

# If you have more than 8 stations, change this value.
NUMBER_OF_STATIONS = 8

# The longest a station can run for by default is 30 minutes. This allows
# the operating system a way to look for stations that have been running too 
# long because of a software problem. Change this as needed.
MAX_MINUTES_PER_STATION = 30

try:
    import RPi.GPIO as GPIO
except ImportError:
    # If you aren't running this on a Pi, you won't have 
    # the GPIO avaialble, so there is a file in utilities that 
    # stubs out the necessary values.
    import utilities.gpio_dev as GPIO

class OpenSprinkler():

    ### Low-Level Hardware Stuff. Don't mess with these. ###

    def _enable_shift_register_output(self):
        """
        Low-level function to enable shift register output. Don't call this
        yourself unless you know why you are doing it.
        """
        GPIO.output(self.PIN_SR_NOE, False)

    def _disable_shift_register_output(self):
        """
        Low-level function to disable shift register output. Don't call this
        yourself unless you know why you are doing it.
        """
        GPIO.output(self.PIN_SR_NOE, True)

    def _set_shift_registers(self, new_values):
        """
        This is the low-level function that is called to set the shift registers.
        I don't pretent do understand the inner workings here, but it works. Don't 
        use this to turn on/off stations, use set_station_status() as the 
        higher-level interface.
        """
        GPIO.output(self.PIN_SR_CLK, False)
        GPIO.output(self.PIN_SR_LAT, False)

        for s in range(0, self.number_of_stations):
            GPIO.output(self.PIN_SR_CLK, False)
            GPIO.output(self.PIN_SR_DAT, new_values[self.number_of_stations-1-s])
            GPIO.output(self.PIN_SR_CLK, True)

        GPIO.output(self.PIN_SR_LAT, True)

    def _initialize_hardwdare(self):
        """
        This contains the low-level stuff required to make the GPIO operations work. Someone 
        smarter than me wrote this stuff, I just smile and nod.
        """
        self.PIN_SR_CLK = 4
        self.PIN_SR_NOE = 17
        self.PIN_SR_LAT = 22
        self.PIN_SR_DAT = 21

        # The 2nd revision of the RPI has a different pin value
        if GPIO.RPI_REVISION == 2:
            self.PIN_SR_DAT = 27

        # Not sure why this is called, but it was in the original script.
        GPIO.cleanup()

        # setup GPIO pins to interface with shift register. Don't muck with this
        # stuff unless you know why you are doing it.
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.PIN_SR_CLK, GPIO.OUT)
        GPIO.setup(self.PIN_SR_NOE, GPIO.OUT)        

        self._disable_shift_register_output()        

        GPIO.setup(self.PIN_SR_DAT, GPIO.OUT)
        GPIO.setup(self.PIN_SR_LAT, GPIO.OUT)

        self._set_shift_registers(self.station_values)
        self._enable_shift_register_output()

    def cleanup(self):
        """
        This runs at the termination of the file, turning off all stations, making 
        sure that any PID files are removed, and running GPIO cleanup.
        """
        self.log("Running Cleanup.")
        self.reset_all_stations()
        self.remove_status_file()
        GPIO.cleanup()

    ### Convenience methods for filesystem operations. You don't need to call these 
    ### manually, they are handled by the higher-level operations.

    def create_status_file(self, station_number):
        """
        Writes a PID file to the directory to indicate what the PID of the 
        current program is and what zone is being operated.
        """
        file_path = os.path.join(CUR_DIR, '%s.pid' % self.pid)
        f = open(file_path, 'w')
        f.write("%d" % station_number)
        f.close()

    def remove_status_file(self):
        """
        Handles removal of the PID file.
        """
        file_path = os.path.join(CUR_DIR, '%s.pid' % self.pid)
        if os.path.exists(file_path):
            os.remove(file_path)

    ### Logging functionality ###

    def log(self, message):
        """
        A convenience method for writing operations to a log file. If debugging 
        is enabled, the message is output to the console.
        """
        file_path = os.path.join(CUR_DIR, 'log.txt')
        f = open(file_path, 'a')
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = '%s\t%s\t%s\n' % (now_time, self.pid, message)
        f.write(msg)
        if self.debug:
            print msg

    ### Higher-Level Interface. These are the functions you want to call

    def operate_station(self, station_number, minutes):
        """
        This is the method that operates a station. Running it causes any 
        currently-running stations to turn off, then a pid file is created that 
        lets the system know that there is a process running. When it completes, 
        ALL stations are turned off and the file is cleaned up.
        """
        self.log("Operating station %d for %d minutes." % (station_number, minutes))

        # First, set all stations to zero
        station_values = [0] * self.number_of_stations

        # Next, enable just the station to run (adjusting for 0-based index)        
        station_values[station_number-1] = 1

        # Send the command
        self._set_shift_registers(station_values)

        # Create a filesystem flag to indicate that the system is running
        self.create_status_file(station_number)

        # After the number of minutes have passed, turn it off
        time_to_stop = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        
        while True:
            if datetime.datetime.now() < time_to_stop:
                pass
            else:
                self.log("Finished operating station.")
                self.remove_status_file()
                self.reset_all_stations()
                break

    def get_station_status(self, station_number):
        """
        This isn't currently used, but it returns the in-memory state of stations.
        """
        return self.station_values

    def reset_all_stations(self):
        """
        A convenience method for turning everything off. 
        """
        self.log("Turning Off All Stations.")
        off_values = [0] * self.number_of_stations
        self._set_shift_registers(off_values)

    def __init__(self, debug=False, number_of_stations=8):
        
        self.number_of_stations = number_of_stations
        
        # If debug is true, we print log messages to console
        self.debug = debug
        
        # We need to save the PID of the current process.
        self.pid = os.getpid()
        
        # Initial values are zero (off) for all stations.
        self.station_values = [0] * number_of_stations

        # Get the hardware ready for operations
        self._initialize_hardware()
        

if __name__ == "__main__":

    # Parse command-line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('--station', type=int, help='Station to run [1-8]', required=True)
    parser.add_argument('--minutes', type=int, help='Number of minutes to run station.', required=True)
    parser.add_argument('--debug', help='Output debugging information', required=False, default=False, action="store_true")

    args = vars(parser.parse_args())
    
    station_number = args['station']
    number_minutes = args['minutes']
    debug = args['debug']

    # Make sure the station is within bounds 
    if station_number not in range(0, NUMBER_OF_STATIONS+1):
        sys.exit("Station Number Must Be 1-8, use 0 if you want to turn everything off.")

    # Make sure they aren't trying to run a station longer than what is allowed
    if number_minutes > MAX_MINUTES_PER_STATION:
        sys.exit("Maximum Minutes Allowed is %d." % MAX_MINUTES_PER_STATION)

    sprinkler = OpenSprinkler(debug=debug, number_of_stations=NUMBER_OF_STATIONS)

    # See if we have a dealy in place to prevent the operation
    if os.path.exists(os.path.join(CUR_DIR, 'DELAY')):
        sprinkler.log("Found DELAY file. Aborting operations.")
        sprinkler.cleanup()
        sys.exit()
    
    # We register the cleanup method to make sure everything is 
    # properly closed out, even if an error occurs.
    atexit.register(sprinkler.cleanup)

    # If they pass station zero, we assume that to be an "all off" command.
    if station_number > 0:
        sprinkler.operate_station(station_number, number_minutes)
    else:
        # We don't actually do anything here, since the stations will automatically
        # be reset when the file exits.
        sprinkler.log('Received all off command.')
