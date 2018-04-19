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

"""
Initial Calibration
Place nothing on the scale, run the calibration.py and record the output. This is the offset.
Place a known weight like 1kg(1000g) on the scale, record the output as weight.
Calculate the ratio:

ratio = (w - offset) / 1000

1000 being the 1000 grams or the weight previously placed on scale

Edit the example.py file with the offset and ratio

def setup():
    hx.set_offset(`Place offset here`)
    hx.set_scale(`Place ratio here`)
    hx.tare()
    pass

Finally, weight (in grams) is
w = (averageValue() - offset) / ratio;

Unit conversion:
0g = 0kg = 0oz = 0pound
1000g = 1kg = 35.274oz = 2.20462 pound
"""
import RPi.GPIO as GPIO
import time
import sys
import statistics

# TODO: Work in Progress

class HX711_2:
    """ 2 Sensors, Only gain=128 is supported """

    def __init__(self, dout_1, pd_sck_1, dout_2=None, pd_sck_2=None):
        """
        Set GPIO Mode, and pin for communication with the 2 HX711 chips
        """
        # Setup the gpio pin numbering system
        GPIO.setmode(GPIO.BCM)

        # Set the pin numbers
        self.DOUT_1   = dout_1
        self.PD_SCK_1 = pd_sck_1

        self.DOUT_2   = dout_2
        self.PD_SCK_2 = pd_sck_2

        # Setup the GPIO Pins as input
#        GPIO.setup(self.DOUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.DOUT_1, GPIO.IN)
        GPIO.setup(self.DOUT_2, GPIO.IN)

        # Setup the GPIO Pins as output
        GPIO.setup(self.PD_SCK_1, GPIO.OUT)
        GPIO.setup(self.PD_SCK_2, GPIO.OUT)
        # -------------------------------------
        
        self.OFFSET = 0
        self.RATIO  = 1
        self.RATIOS = [(0,1) for _ in range(4)] # (measured sensor data @ reference weight), calculated ratio)

        # Low-pass Filter
        self.KERNEL = [1, 2, 4, 8, 16, 8, 4, 2, 1]
        # self.KERNEL = [1, 2, 4, 8, 16, 32] # TODO
        self.KSIZE  = len(self.KERNEL)
        self.NORM   = sum(self.KERNEL)

        # Used to keep average sensor(s) data
        self.AVALUE = 0; # Initial value set in tare()

        # Power up the chip
        self.reset()
        self.AVALUE = self.read_average_no_spikes(9) # In case tare() is not called


    def set_offset(self, offset):
        self.OFFSET = offset


    def set_ratio(self, ratio):
        self.RATIO = ratio


    def set_ratios(self, ratio_1=(0,1), ratio_2=(0,1), ratio_3=(0,1), ratio_4=(0,1)):
        """
        Set offset - ratio pairs
        """
        self.RATIOS[0] = ratio_1
        self.RATIOS[1] = ratio_2
        self.RATIOS[2] = ratio_3
        self.RATIOS[3] = ratio_4


    def get_interpolated_ratio(self, measured_value):
        """
        Linear Interpolation: ratio = ratio_a + (ratio_b - ratio_a) * ((value - value_a) / (value_b - value_a))
        Assumption: self.RATIOS[X][0] (i.e., raw data @ reference weight) are monotonically increasing
        """
        if   measured_value <= self.RATIOS[0][0]: return self.RATIOS[0][1] # out of range
        elif measured_value >= self.RATIOS[3][0]: return self.RATIOS[3][1] # out of range
        else:
            idx = 0
            for i in range(len(self.RATIOS)-1):
                if self.RATIOS[i][0] < measured_value and measured_value < self.RATIOS[i+1][0]:
                    idx = i
                    break

            k = (measured_value - self.RATIOS[i][0]) / (self.RATIOS[i+1][0] - self.RATIOS[i][0])
            return self.RATIOS[i][1] + k * (self.RATIOS[i+1][1] - self.RATIOS[i][1])


    def read(self, DOUT, PD_SCK):
        """
        Read data from the HX711 chip
        https://cdn.sparkfun.com/datasheets/Sensors/ForceFlex/hx711_english.pdf
        """

        # Wait until the chip is ready
        while GPIO.input(DOUT) == 1:
            pass

        count = 0

        for i in range(24):
            count = count << 1
            GPIO.output(PD_SCK, True)
            GPIO.output(PD_SCK, False)
            # Read after falling edge
            if(GPIO.input(DOUT) == 1):
                count += 1

        # 25 SCKs -> next gain = 128
        GPIO.output(PD_SCK, True)
        GPIO.output(PD_SCK, False)

        count = count ^ 0x800000
        return count


    def read_running_average(self):
        value = self.read(self.DOUT_1, self.PD_SCK_1)

        if self.DOUT_2 != None and self.PD_SCK_2 != None:
            value += self.read(self.DOUT_2, self.PD_SCK_2)
               
        self.AVALUE = (self.AVALUE + value) / 2
        return self.AVALUE


    def read_average(self, times=16):
        """
        Calculate average value from sensor data samples
        :param times: read x samples to get average
        """
        sum = 0
        for i in range(times):
            sum += read_running_average()
        return sum / times


    def read_average_no_spikes(self, times=25):
        """
        Remove spikes
        """
        cut = times//5 # discard remainder
        values = sorted([self.read_running_average() for i in range(times)])[cut:-cut]
        return statistics.mean(values)


    def read_average_LPF(self):
        """
        """
        values = [self.read_running_average() for i in range(self.KSIZE)]
        return sum([k*v for (k, v) in zip(self.KERNEL, values)]) / self.NORM


    def to_grams(self, value):
        """
        :param value: to be converted to grams
        :return float weight in grams
        """
        # TODO: ratio or (offset,ratio) pairs must be set. How to check?
        if self.RATIO != 1:
            return (value - self.OFFSET) / self.RATIO
        else: 
            return (value - self.OFFSET) / self.get_interpolated_ratio( value )


    def round_to(self, value, res):
        """
        Round to e.g., 0.5, 0.02, 10, etc.
        """
        if res == 0:
            return round(value)
        return res * (round(value/res))


    def tare(self, times=9):
        """
        Tare functionality for calibration
        :param times: set value to calculate average
        """
        self.AVALUE = self.read_average_no_spikes(times)
        self.set_offset(self.AVALUE)


    def power_down(self, PD_SCK):
        """
        Power the chip down
        """
        GPIO.output(PD_SCK, False)
        GPIO.output(PD_SCK, True)
        time.sleep(0.001)


    def power_up(self, PD_SCK):
        """
        Power the chip up
        """
        GPIO.output(PD_SCK, False)
        time.sleep(0.001)


    def reset(self):
         self.power_down(self.PD_SCK_1)
         self.power_up(self.PD_SCK_1)
         
         if self.DOUT_2 != None and self.PD_SCK_2 != None:
            self.power_down(self.PD_SCK_2)
            self.power_up(self.PD_SCK_2)
