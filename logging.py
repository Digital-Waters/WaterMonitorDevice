from datetime import datetime
import os
import platform
import shutil
import json

folder = "logs"
filename = os.path.join(folder, "systemLogs.txt")


def writeFile(eventTitle, eventDisc):
    os.makedirs(folder, exist_ok=True)
    deviceID = "12345"
    currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #eventTitle = "test"
    #eventDisc = "testing log file"
    osVersion = platform.version()
    location = {'latitude': 51.509865, 'longitude': -0.118092}
    battery = "45%"
    total, used, free = shutil.disk_usage("/")

    freeGB = free / (1024 ** 3)
    
    data = {
    "time": currentTime,
    "Device ID": deviceID,
    "Event Title": eventTitle,
    "Event Discription": eventDisc,
    "System OS version": osVersion,
    "Location": location,
    "Battery": battery,
    "Storage remaining": f'{freeGB} GB'
    }
    
    try:
        logs = []
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'r') as f:
                try:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = [logs]
                except json.JSONDecodeError:
                    logs = []
        else:
            logs = []

        # Append new data to the logs
        logs.append(data)


        with open(filename, 'w') as f:
            json.dump(logs, f, indent=4)
            print(data)
            
        size = os.path.getsize(filename)/100000
        
        if size > 50:
            makeStorage()
        print(f"{size} bytes")
    except OSError as e:
        print(f"Error: {e}")

def makeStorage():
    with open(filename, 'r') as file:
        logData = json.load(file)
        
    totalItems = len(logData)
    print(totalItems)
    itemsToDelete = round(totalItems * 0.1)
    print(itemsToDelete)
    
    if itemsToDelete > 0:
        logData = logData[itemsToDelete:]


    # Step 4: Write the modified data back to the JSON file
    with open(filename, 'w') as file:
        json.dump(logData, file, indent=4)

if __name__ == "__main__":
    try:
        writeFile("Test","this is a test")
    except KeyboardInterrupt:
        quit()

