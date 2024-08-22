import time
import logging

import cameraSensor
import temperatureSensor


interval = 5  # Set interval in seconds

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sampleTask():
    # Example task 1
    logging.info("in sampleTask()")
    # Rename this function, add your task implementation here
    # e.g., capture image, read sensor data make a function / file for each sensor. 
    # Assume a variable number of sensors where some won't be present.
    pass

def capturePhoto():
    #cameraSensor.capture_image_with_timestamp()
    logging.info("in takePhoto()")

def captureTemperature():
    #temperatureSensor.sensor()
    logging.info("in captureTemperature()")

def main():
    # Main loop. Put all individual sensor code here. 
    # The idea is to loop over every sensor at every interval, gather all 
    # the sensor data into a .json file, and upload it asap. 

    logging.info("Starting main loop...")

    while True:
        try:
            sampleTask()
            capturePhoto()
            captureTemperature()
            #captureOxygen()
            #capturepH()
            #captureLongLat()
            #captureConductivity()
            #captureTerpidity()

            #sendDataPayload()
            
            logging.info(f"Sleeping for {interval} seconds...")
            time.sleep(interval)

        except KeyboardInterrupt:
            logging.info("Shutting down...")
            break

        except Exception as e:
            logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
