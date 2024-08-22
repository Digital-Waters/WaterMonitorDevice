import time
import logging

import cameraSensor
import temperatureSensor


interval = 5  # Set interval in seconds


def main():
    # Main loop. Put all individual sensor code here. 
    # The idea is to loop over every sensor at every interval, gather all 
    # the sensor data into a .json file, and upload it asap. 

    log = initlog()
    log.info("Starting main loop...")

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
            
        except KeyboardInterrupt:
            log.info("Shutting down...")
            break

        except Exception as e:
            log.error(f"In main(). An error occurred: {e}")

        finally:
            log.info(f"*** In main(). Sleeping for {interval} seconds...")
            time.sleep(interval)


def initlog():
    # Create a custom log
    log = logging.getLogger('DWLogger')

    # Clear existing handlers to prevent duplicate logs
    if log.hasHandlers():
        log.handlers.clear()

    #log.propagate = False

    # Set the overall logging level (can be adjusted as needed)
    log.setLevel(logging.DEBUG)

    # Create handlers
    console_handler = logging.StreamHandler()  # Outputs to the CLI
    file_handler = logging.FileHandler('waterDeviceLog.txt')  # Outputs to a file

    # Set logging levels for each handler
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add them to the handlers
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # Add the handlers to the logger
    log.addHandler(console_handler)
    log.addHandler(file_handler)

    return log

def sampleTask():
    # Example task 1
    logging.info("in sampleTask()")
    # Rename this function, add your task implementation here
    # e.g., capture image, read sensor data make a function / file for each sensor. 
    # Assume a variable number of sensors where some won't be present.
    pass


def capturePhoto():
    cameraSensor.captureCameraImage()
    

def captureTemperature():
    temperatureSensor.captureTemperature()
    


if __name__ == "__main__":
    main()
