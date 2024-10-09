import time
import Adafruit_ADS1x15  # Assuming you're using ADS1115 for analog input

# Initialize the ADC (Analog-to-Digital Converter)
adc = Adafruit_ADS1x15.ADS1115()

# Gain settings for the ADC (optional, depending on your setup)
GAIN = 1

def read_conductivity():
    # Read the analog value from the sensor (A3 is the channel in this case)
    value = adc.read_adc(3, gain=GAIN)
    
    # Convert the raw ADC value to TDS or conductivity (you will need the formula from your sensor's datasheet)
    conductivity = convert_to_conductivity(value)
    
    return conductivity

def convert_to_conductivity(adc_value):
    # Add your conversion logic here
    # This will depend on your sensor and calibration process
    # Example:
    conductivity = adc_value * 0.5  # Modify this based on your sensor's formula
    return conductivity

if __name__ == "__main__":
    while True:
        conductivity = read_conductivity()
        print(f"Conductivity: {conductivity} μS/cm")
        
        # Wait before reading again (you can adjust the delay as needed)
        time.sleep(2)
