import time
import Adafruit_ADS1x15

# Initialize the ADC (Analog-to-Digital Converter)
adc = Adafruit_ADS1x15.ADS1115()

# Gain settings for the ADC (use the appropriate gain for your sensor's range)
GAIN = 1

def read_conductivity():
    num_samples = 10
    total_value = 0
    
    for _ in range(num_samples):
        # Read the analog value from the sensor (A3 is the channel in this case)
        value = adc.read_adc(3, gain=GAIN)
        total_value += value
        time.sleep(0.05)  # Small delay between readings

    # Average the readings to reduce noise
    avg_value = total_value / num_samples

    # Print the raw ADC value to see the baseline in air
    print(f"Raw ADC Value: {avg_value}")
    
    # Convert the averaged raw ADC value to conductivity
    conductivity = convert_to_conductivity(avg_value)

    return conductivity

def convert_to_conductivity(adc_value):
    # Increase threshold to filter out noise in the air
    threshold = 930  # Adjust this threshold based on baseline readings in air
    conversion_factor = 0.5  # Your sensor-specific factor

    if adc_value < threshold:
        return 0.0  # Consider it as no conductivity (air)

    conductivity = adc_value * conversion_factor
    return conductivity

if __name__ == "__main__":
    while True:
        conductivity = read_conductivity()
        print(f"Conductivity: {conductivity:.2f} μS/cm")

        # Wait before reading again (you can adjust the delay as needed)
        time.sleep(2)
