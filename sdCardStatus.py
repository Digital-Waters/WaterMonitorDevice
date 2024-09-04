#import os
import shutil

def sdCardStorageStatus():
    # Get the disk usage statistics for the root partition where the SD card is mounted
    total, used, free = shutil.disk_usage("/")

    # Convert the total and free space to kilobytes (KB)
    #total_kb = total // 1024
    free_kb = free // 1024

    # Calculate the percentage of the total storage that is still available
    available_percentage = (free / total) * 100

    # Create a dictionary with the required information
    storage_status = {
        "total_space_remaining_kb": free_kb,
        "available_percentage": round(available_percentage, 2)  # rounding to 2 decimal places for clarity
    }


    print(storage_status)

    return storage_status


#sdCardStorageStatus()
