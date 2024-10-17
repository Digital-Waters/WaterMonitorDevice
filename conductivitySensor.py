import time
import Adafruit_ADS1x15

# Initialize the ADC (Analog-to-Digital Converter)
adc = Adafruit_ADS1x15.ADS1115()

# Gain settings for the ADC (try adjusting the gain for proper readings)
GAIN = 2  # Change this as needed: 1, 2, 4, 8, or 16

def read_conductivity():
    try:
        num_samples = 10
        total_value = 0

        for _ in range(num_samples):
            # Read the analog value from the sensor (A3 is the channel in this case)
            value = adc.read_adc(3, gain=GAIN)
            total_value += value
            time.sleep(0.05)  # Small delay between readings

        # Average the readings to reduce noise
        avg_value = total_value / num_samples

        # Print the raw ADC value to observe baseline readings in air and water
        print(f"Raw ADC Value: {avg_value}")

        # Convert the averaged raw ADC value to conductivity
        conductivity = convert_to_conductivity(avg_value)

        return conductivity

    except Exception as e:
        print(f"Error reading sensor: {e}")
        return None

def convert_to_conductivity(adc_value):
    # Adjust threshold based on baseline readings in air
    threshold = 1250  # Adjust this based on actual air baseline readings
    conversion_factor = 0.5  # Experiment with this value for accuracy

    if adc_value < threshold:
        return 0.0  # Consider it as no conductivity (air)

    conductivity = adc_value * conversion_factor
    return conductivity

if __name__ == "__main__":
    try:
        while True:
            print("Reading in air (baseline):")
            # Test with sensor in the air to get baseline reading
            conductivity_air = read_conductivity()
            if conductivity_air is not None:
                print(f"Conductivity in air: {conductivity_air:.2f} μS/cm")

            input("Now place the sensor in water and press Enter to continue...")

            print("Reading in water:")
            # Test with sensor in water to get water reading
            conductivity_water = read_conductivity()
            if conductivity_water is not None:
                print(f"Conductivity in water: {conductivity_water:.2f} μS/cm")

            # Wait before reading again (adjust the delay as needed)
            time.sleep(2)

    except KeyboardInterrupt:
        print("Program stopped by user")
