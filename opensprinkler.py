import os
import sys
import time
import atexit
import datetime
import argparse

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

try:
    import RPi.GPIO as GPIO
except ImportError:
    import utilities.gpio_dev as GPIO

class OpenSprinkler():

    def enable_shift_register_output(self):
        GPIO.output(self.PIN_SR_NOE, False)

    def disable_shift_register_output(self):
        GPIO.output(self.PIN_SR_NOE, True)

    def set_shift_registers(self, new_values):

        GPIO.output(self.PIN_SR_CLK, False)
        GPIO.output(self.PIN_SR_LAT, False)

        for s in range(0, self.number_of_stations):
            GPIO.output(self.PIN_SR_CLK, False)
            GPIO.output(self.PIN_SR_DAT, new_values[self.number_of_stations-1-s])
            GPIO.output(self.PIN_SR_CLK, True)

        GPIO.output(self.PIN_SR_LAT, True)

    def set_station_status(self, station_number, new_status):
        
        # Make sure only a 0 or 1 was passed.
        if not new_status in (0,1):
            self.log("Invalid value for station. Must be 0 or 1.")
            return
        
        self.station_values[station_number] = new_status
        self.set_shift_registers()

    def create_status_file(self, station_number):
        file_path = os.path.join(CUR_DIR, '%s.pid' % self.pid)
        f = open(file_path, 'w')
        f.write("%d" % station_number)
        f.close()

    def remove_status_file(self):
        file_path = os.path.join(CUR_DIR, '%s.pid' % self.pid)
        if os.path.exists(file_path):
            os.remove(file_path)

    def log(self, message):
        file_path = os.path.join(CUR_DIR, 'log.txt')
        f = open(file_path, 'a')
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = '%s\t%s\t%s\n' % (now_time, self.pid, message)
        f.write(msg)
        if self.debug:
            print msg

    def operate_station(self, station_number, minutes):

        self.log("Operating station %d for %d minutes." % (station_number, minutes))

        # First, set all stations to zero
        station_values = [0] * self.number_of_stations

        # Next, enable just the station to run (adjusting for 0-based index)        
        station_values[station_number-1] = 1

        # Send the command
        self.set_shift_registers(station_values)

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
        return self.station_values

    def reset_all_stations(self):
        self.log("Turning Off All Stations.")
        off_values = [0] * self.number_of_stations
        self.set_shift_registers(off_values)

    def cleanup(self):
        self.log("Running Cleanup")
        self.reset_all_stations()
        self.remove_status_file()
        GPIO.cleanup()
    
    def __init__(self, debug=False, number_of_stations=8):
        
        self.number_of_stations = number_of_stations
        
        # If debug is true, we print log messages to console
        self.debug = debug
        
        # We need to save the PID of the current process
        self.pid = os.getpid()
        
        # Initial values are zero (off)
        self.station_values = [0] * number_of_stations

        self.PIN_SR_CLK = 4
        self.PIN_SR_NOE = 17
        self.PIN_SR_LAT = 22
        self.PIN_SR_DAT = 21

        # The 2nd revision of the RPI has a different pin value
        if GPIO.RPI_REVISION == 2:
            self.PIN_SR_DAT = 27

        # Not sure why this is called, but it was in the original script.
        GPIO.cleanup()
        
        # setup GPIO pins to interface with shift register
        GPIO.setmode(GPIO.BCM)
        
        GPIO.setup(self.PIN_SR_CLK, GPIO.OUT)
        GPIO.setup(self.PIN_SR_NOE, GPIO.OUT)
        
        self.disable_shift_register_output()
        
        GPIO.setup(self.PIN_SR_DAT, GPIO.OUT)
        GPIO.setup(self.PIN_SR_LAT, GPIO.OUT)

        self.set_shift_registers(self.station_values)
        self.enable_shift_register_output()
        

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

    if station_number not in range(0,9):
        sys.exit("Station Number Must Be 0-8.")

    if number_minutes > 30:
        sys.exit("Maximum Minutes Allowed is 30.")

    sprinkler = OpenSprinkler(debug=debug, number_of_stations=8)

    # See if we have a stop in place
    if os.path.exists(os.path.join(CUR_DIR, 'DELAY')):
        sprinkler.log("Found DELAY file. Aborting job.")
        sprinkler.cleanup()
        sys.exit()
    
    # We register the cleanup method to make sure everything is 
    # properly closed out, even if an error occurs.
    atexit.register(sprinkler.cleanup)

    # If they pass station zero, we assume that to be an "all off" command.
    if station_number > 0:
        sprinkler.operate_station(station_number, number_minutes)
    else:
        sprinkler.log('Received all off command.')

