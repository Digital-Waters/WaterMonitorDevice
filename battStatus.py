# pip install psutil
# code not tested on board yet

import psutil
import time

def getBatteryStatus():
    # Retrieve battery status
    battery = psutil.sensors_battery()
    if battery is None:
        return "No battery information available. Are you sure you're running on a laptop?"

    # Extract the details
    percent = battery.percent
    is_plugged = battery.power_plugged
    time_left = battery.secsleft

    # Determine charging or discharging status
    status = "Charging" if is_plugged else "Discharging"

    # Format time left
    if time_left == psutil.POWER_TIME_UNLIMITED:
        time_left_str = "Calculating..."
    elif time_left == psutil.POWER_TIME_UNKNOWN:
        time_left_str = "Unknown"
    else:
        hours, minutes = divmod(time_left // 60, 60)
        time_left_str = f"{int(hours)}h {int(minutes)}m"

    # Return a formatted string with the battery information
    return f"Battery Status: {percent}% | {status} | Time Left: {time_left_str}"

def monitorBattery(interval=60):   # interval can be changed to suit our desired intent
    try:
        while True:
            status = getBatteryStatus()
            print(status)
            time.sleep(interval)  # Wait for the specified interval before checking again
    except KeyboardInterrupt:
        print("Battery monitoring stopped.")
        
        
#monitorBattery()
