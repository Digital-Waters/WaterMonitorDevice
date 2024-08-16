import time

# Path to the LED control file
led_path = "/sys/class/leds/mmc0/brightness"

# Blink the LED
try:
    while True:
        # Turn the LED on
        with open(led_path, 'w') as led_file:
            led_file.write('1')
        time.sleep(1)
        
        # Turn the LED off
        with open(led_path, 'w') as led_file:
            led_file.write('0')
        time.sleep(1)
except KeyboardInterrupt:
    # Turn off the LED when exiting the program
    with open(led_path, 'w') as led_file:
        led_file.write('0')
