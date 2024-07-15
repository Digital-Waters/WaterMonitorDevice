# WaterMonitorDevice
All the code that runs on our water monitoring devices. 





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

#### 2. Software Installation
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

#### 3. Testing the Camera Module
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