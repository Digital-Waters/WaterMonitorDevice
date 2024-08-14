import time
import logging
#import Payload
#import cameraSensor
import temperatureSensor


interval = 5  # Set interval in seconds
payloadData = {}

# Configure logging

def sampleTask():
    # Example task 1
    # Rename this function, add your task implementation here
    # e.g., capture image, read sensor data
    # make a function / file for each sensor. Assume a variable number of sensors where some won't be present.
    pass

def capturePhoto():
    #cameraSensor.capture_image_with_timestamp()
    logging.writeFile("Picture", "Picture was successfully taken!")


def captureTemperature():
    temp = temperatureSensor.sensor()
    #payloadData.update({"temperature": temp})
    pass

def sendDataPayload():

    pass

def main():
    # Main loop. Put all individual sensor code here. 
    # The idea is to loop over every sensor at every interval, gather all 
    # the sensor data into a .json file, and upload it asap. 

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
            
            time.sleep(interval)

        except KeyboardInterrupt:
            break

        except Exception as e:
            logging.writeFile("error", "Error in the main loop")
            time.sleep(interval)
            print(e)

if __name__ == "__main__":
    main()
