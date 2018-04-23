"""
HX711 Load cell amplifier Python Library
Original source: https://gist.github.com/underdoeg/98a38b54f889fce2b237
Documentation source: https://github.com/aguegu/ardulibs/tree/master/hx711
Adapted by 2017 Jiri Dohnalek

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

# TODO Make it a class

import RPi.GPIO as GPIO
import time
import sys
from hx711   import HX711
from hx711_2 import HX711_2

# Contain tuples of (reference weight, measured offset, calculated ratio)
mylist   = []
offset   = 0
avrg     = 0
filename = "calibration_data.txt"

#hx = HX711(dout=5, pd_sck=6)
#hx = HX711(dout=20, pd_sck=21)
hx = HX711_2(dout_1=5, pd_sck_1=6, dout_2=20, pd_sck_2=20)


def cleanAndExit():
    print "Cleaning..."
    GPIO.cleanup()
    print "Bye!"
    sys.exit()


def loop():
    global avrg
    
    idx = 0
    samples = [0, 0, 0, 0]

    print 'Samples                                                         Average'

    try:
        hx.reset()

        for i in range(4):
            samples[i] = hx.read_average_LPF() # including running average
#            samples[i] = hx.read_average_no_spikes(times=9) # Try as well?
            print samples[i], ',',

        avrg = (samples[0] + samples[1] + samples[2] + samples[3]) / 4.0
        print '        ', avrg
        
    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()


def set_data( ref_weight, measured_value, offset ):
    if ref_weight == 0:
        print( "Reference weight cannot be 0" )
        return
    ratio = round((measured_value - offset) / ref_weight, 3)
    mylist.append((ref_weight, measured_value, ratio))
    

def write_data():
    """ Store the measured offsets/calculated ratios to file
    """
    with open(filename, 'w') as f:
        f.write('\n'.join('%s, %s, %s' % x for x in mylist))
        print( "Data written to", filename )


def initial_offset():
    global offset
    global mylist
    
    print( "First measurement without a reference weight, press 'Enter' when ready" )
    q = input()
    loop()
    offset = avrg
    mylist.append((0, avrg, 1))
    

##################################

if __name__ == "__main__":
    
    initial_offset()
    
    while True:
        print( "Enter the reference weight being used and press 'Enter' when ready, 'q' for quit" )
        q = input()
        
        if q == 'q':
            write_data()
            print( mylist )
            cleanAndExit()

        elif q.replace('.','',1).isdigit(): # works for positive int and float
            loop()
            set_data(eval(q), avrg, offset)

        else:
            print( "Wrong reference weight!" )
