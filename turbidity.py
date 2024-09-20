import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time
import RPi.GPIO as GPIO



def getReading(log, temp): 

    if temp < 5 or temp > 90:
        return False

    NTU = 0
    try: 
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, gain=1)
        chan = AnalogIn(ads, ADS.P0)

        num_samples = 200
        vol = 0

        # Read ADC value multiple times to average
        for i in range(num_samples):
            voltage = (chan.value/32767)*4.8   
            vol += voltage
            time.sleep(0.1)  
        
        # Calculate average voltage
        averageVol = vol / num_samples

        if averageVol < 2.5:
            NTU = 3000  # Example for very turbid water
        else:
            NTU = -1120.4 * (averageVol ** 2) + 5742.3 * averageVol - 4352.8
        
        if NTU < 0:
            NTU = 0  # Set to 0 NTU for negative voltage
        
        log.info(f"In Turbidity task: successfully got Turbidity (NTU): {NTU:.2f}")

    except Exception as e:
        log.error(f"In Turbidity error getting data: {e}")
        return False
    finally:
        return NTU
