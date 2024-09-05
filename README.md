# WaterMonitorDevice
All the code that runs on our water monitoring devices. 

Our monitoring devices are the basis of our operation. They generate all the data that we use to find actionable insights. As such, it's extremely immportant that the data they create is consistent and the photo's of water are captured with specific hardware and configuration settings.

The big idea behind our system is to find patterns in lots of data. Taking a photo of water is relatively inexpensive. By taking the photo underwater, in a light-contained enclosure, we're removing all light as a variable in our data. 
Because the only light all our devices will use is the same, we can take photos regardless of external conditions (like time of day, weather, shade, etc) and ensure our data is consistent. For this reason, we also insist all our devices use the same camera. Different camera manufacteurers will have small differences in the image and light quality that can impact our data. 

These devices will be bought and maintained by field volunteers. People who might have zero technical know-how. 
As such, ensure that any work you do is done in the spirit of making their lives and volunteer duties as easy as possible.

# Contribution Guidelines
There are plenty of issues that are open that represent work that needs to be done. You can choose something there to get started or create your own issues. 
There is nothing too small. If you see any spelling or grammar errors, or no documentation at all, please feel free to create an issues and submit a pull request. 
All contributions / pull requests will need to be approved by Digital Waters engineering. 

Please introduce yourself in our repo Discussions board! 
We'd love to connect and collaborate with like-minded people. Don't be a stranger :D

## Testing the Camera Code on Raspberry Pi Zero 2 W
Before uploading the cam_code make sure the pi is tested for the camera module and working

### Requirements
1. Raspberry Pi Zero 2 W
2. Camera Module (e.g., Raspberry Pi Camera Module V2)
3. Camera Ribbon Cable
4. MicroSD Card (with Raspberry Pi OS installed)
5. Power Supply
6. Display and Keyboard/Mouse (or remote access setup)

### Step-by-Step Guide
#### 1. Hardware Setup
1. Power Off the Raspberry Pi: Ensure the Raspberry Pi Zero 2 W is powered off before connecting any hardware.
2. Connect the Camera Module: 
   - Attach the camera module to the Raspberry Pi Zero 2 W using the camera ribbon cable.
   - Ensure the blue side of the cable is facing away from the Raspberry Pi board and insert the cable into the camera connector (CSI port) on the Raspberry Pi. Secure the connector by gently pressing the tabs on either side.
3. Insert the MicroSD Card: Make sure the MicroSD card with the Raspberry Pi OS installed is inserted into the Raspberry Pi.

#### 2. Connecting to your Raspberry Pi
We use SSH to connect to our RPi. 
On Windows: WinSCP, Putty. Visual Studio also has plugins that enable this.

#### 3. Software Installation
1. Power On the Raspberry Pi: Connect the power supply to the Raspberry Pi Zero 2 W and wait for it to boot up.
2. Update the System: Open a terminal and run the following commands to update the system:
   ```
   sudo apt-get update
   sudo apt-get upgrade
   ```
3. Enable the Camera Interface: Use the Raspberry Pi Configuration tool to enable the camera interface.
   - Open the Raspberry Pi Configuration tool by running:
     ```
     sudo raspi-config
     ```
   - Navigate to `Interfacing Options` > `Camera` and select `Enable`.
   - Reboot the Raspberry Pi for the changes to take effect:
     ```
     sudo reboot
     ```
4. Install Required Packages: Install the `libcamera` utilities which include `libcamera-hello`.
   ```
   sudo apt-get install libcamera-apps
   ```

#### 4. Testing the Camera Module
1. Check Camera Connection: After rebooting, verify that the camera module is detected by running:
   ```
   vcgencmd get_camera
   ```
   The output should be:
   ```
   supported=1 detected=1
   ```
   This indicates that the camera module is supported and detected.

2. Run `libcamera-hello` Command: Use the `libcamera-hello` command to test the camera module.
   ```
   libcamera-hello
   ```
   This command opens a preview window and displays the live camera feed. This is a good test to ensure that the camera module is working correctly.

3. Capture an Image: Use the `libcamera-still` command to capture an image.
   ```
   libcamera-still -o test_image.jpg
   ```
   This command captures an image and saves it as `test_image.jpg` in the current directory.

4. Record a Video: Use the `libcamera-vid` command to record a video.
   ```
   libcamera-vid -o test_video.h264 -t 10000
   ```
   This command records a 10-second video and saves it as `test_video.h264` in the current directory.

5. View the Captured Image and Video: Use an image viewer or media player to view the captured image and video to ensure the camera module is working correctly.

### Troubleshooting
- Camera Not Detected: If the camera is not detected (`vcgencmd get_camera` returns `detected=0`), check the ribbon cable connection and ensure it is properly seated in the CSI port.
- No Image or Video Output: If no image or video is captured, ensure that the camera interface is enabled in the Raspberry Pi Configuration tool and that the camera module is properly connected.







# Prototyping the temperature Code on Raspberry Pi Zero 2 W
To run the sense_Temp1.py code on a Raspberry Pi Zero 2 W, which is designed to read temperature data from a DS18B20 sensor, you need to follow pre-requisite steps for both hardware and software setup:

### Hardware Setup
1. DS18B20 Sensor: Ensure you have a DS18B20 temperature sensor.
2. Wiring:
   - GND: Connect the GND pin of the DS18B20 to a ground pin on the Raspberry Pi.
   - VCC: Connect the VCC pin of the DS18B20 to a 3.3V or 5V pin on the Raspberry Pi.
   - Data: Connect the data pin of the DS18B20 to a GPIO pin on the Raspberry Pi (e.g., GPIO4).

### Software Setup
1. Enable 1-Wire Interface:
   - Open the Raspberry Pi configuration tool:
     ```
     sudo raspi-config
     ```
   - Navigate to `Interfacing Options` > `1-Wire` and select `Enable`.
   - Reboot the Raspberry Pi to apply the changes:
     ```
     sudo reboot
     ```

2. Install Required Packages:
   - Ensure you have the necessary packages installed:
     ```
     sudo apt-get update
     sudo apt-get install python3 python3-pip
     ```

3. Load 1-Wire Kernel Modules:
   - Ensure the 1-Wire kernel modules are loaded. Add the following lines to `/boot/config.txt`:
     ```
     dtoverlay=w1-gpio
     ```
   - You may also need to manually load the modules:
     ```
     sudo modprobe w1-gpio
     sudo modprobe w1-therm
     ```

4. Check for the Sensor:
   - Verify the sensor is detected. After rebooting, you should see a directory named `/sys/bus/w1/devices/` that contains directories with names starting with `28-` (the DS18B20 sensor's family code). You can check it by:
     ```
     ls /sys/bus/w1/devices/
     ```

### Running the Script
1. Create the Script File:
   - Download the Python script file (`sense_Temp1.py'`).

2. Run the Script:
   - Run the code in an IDE such as Thonny, Geany, etc.

   				OR

   - Make the script executable:
     ```
     chmod +x sense_Temp1.py
     ```
   - Run the script using Python 3:
     ```
     ./sense_Temp1.py
     ```

# Prototyping the GPS Code on Raspberry Pi Zero 2 W
To run the gpsSensor.py code on a Raspberry Pi Zero 2 W, which is designed to read GPS location and time data from a GT-U7 GPS module, you need to follow pre-requisite steps for both hardware and software setup:

### Hardware Setup
1. GT-U7 module: Ensure you have a GT-U7 module.
2. Micro USB
2. Wiring:
    - For now the sensor can be connected using a microUSB.

### Software Setup
1. Edit config.txt file: 
    ```
    sudo nano /boot/config.txt
    ```
    insert the following lines at the bottom of the file: 

    ```
    droverlay=w1-gpio
    dtoverlay=w1-gpio
    ```

2. Install Required Packages:
   - Ensure you have the necessary packages installed:
     ```
     sudo apt-get update
     pip install pynmea2
     pip install pytz 
     ```


3. Check for the Sensor:
   - Verify the sensor is detected and sending data through the USB:
     ```
     sudo apt install minicom
     sudo minicom -b 9600 -o -D /dev/ttyACM0
     ```

### Running the Script
1. Create the Script File:
   - Download the Python script file (`gpsSensor.py'`).

2. Run the Script:
   - Run the code in an IDE such as Thonny, Geany, etc.

   				OR

   - Make the script executable:
     ```
     chmod +x gpsSensor.py
     ```
   - Run the script using Python 3:
     ```
     ./gpsSensor.py
     ```
## Payload Script for Water Monitoring Device

This script (`Payload.py`) is designed to upload photos taken by water monitoring devices to a specified server. The script ensures the data consistency required for analysis by uploading photos with specific hardware and configuration settings.

### Requirements

- Python 3
- Necessary Python Packages: `requests`, `requests-toolbelt`



1. **Update the System:** Open a terminal and run the following commands to update the system:
  ```
   sudo apt-get update
   sudo apt-get upgrade
 ```
2. **Install Required Python Packages:** 
  ```
  sudo apt-get install python3 python3-pip
  pip3 install requests requests-toolbelt
  ```
3. **Create a Virtual Environment: (optional but recommended):** 
  ```
 python3 -m venv myenv
 source myenv/bin/activate
  ```
4. **Run the Script:** 
  ```
python3 Payload.py
  ```
### Troubleshooting
- **Upload Failures**: If uploads fail (500 Internal Server Error), check the server logs for any errors. You can view the logs by using the Heroku CLI:
 ```
heroku logs --tail --app your-heroku-app-name
  ```


