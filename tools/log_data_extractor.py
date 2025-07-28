import re
import json
import os
from datetime import datetime

def parse_log_file(log_file_path, output_file_path):
    with open(log_file_path, 'r') as file:
        log_lines = file.readlines()

    capture_records = {}
    successful_uploads = set()

    # Regex patterns
    image_saved_pattern = re.compile(r"Image saved to (images/.+?/(\w+_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.jpg)")
    rgba_pattern = re.compile(r"RGBA: ({.*})")
    upload_start_pattern = re.compile(r"Uploading file: .*/(\w+\.jpg)")
    device_id_pattern = re.compile(r"- ([0-9a-f]{16}) -")
    timestamp_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    temp_fail_pattern = re.compile(r"No temperature sensor connected.")
    temp_value_pattern = re.compile(r"Temperature: (-?\d+\.?\d*)")
    upload_success_pattern = re.compile(r"Successfully uploaded payload to DB")

    current_record = None
    current_image = None

    for line in log_lines:
        timestamp_match = timestamp_pattern.match(line)
        timestamp = timestamp_match.group(1) if timestamp_match else None

        # Start a new record if image is saved
        image_match = image_saved_pattern.search(line)
        if image_match:
            full_path, image_name = image_match.groups()
            device_id_match = device_id_pattern.search(line)
            device_id = device_id_match.group(1) if device_id_match else None

            current_image = image_name
            capture_records[current_image] = {
                "image": image_name,
                "deviceID": device_id,
                "device_datetime": timestamp,
                "waterColor": None,
                "temperature": None
            }
            continue

        # Extract RGBA info
        rgba_match = rgba_pattern.search(line)
        if rgba_match and current_image:
            try:
                rgba_dict = eval(rgba_match.group(1))  # trusted input from known log
                capture_records[current_image]["waterColor"] = rgba_dict
            except Exception:
                pass
            continue

        # Extract temperature value or note no sensor
        if temp_fail_pattern.search(line) and current_image:
            capture_records[current_image]["temperature"] = None
        else:
            temp_match = temp_value_pattern.search(line)
            if temp_match and current_image:
                capture_records[current_image]["temperature"] = float(temp_match.group(1))

        # Mark uploads that succeeded
        upload_match = upload_start_pattern.search(line)
        if upload_match:
            current_upload = upload_match.group(1)

        if upload_success_pattern.search(line):
            if 'current_upload' in locals():
                successful_uploads.add(current_upload)
                del current_upload

    # Remove successfully uploaded images
    filtered = [
        record for name, record in capture_records.items()
        if name not in successful_uploads
    ]

    # Write to output file
    with open(output_file_path, 'w') as out_file:
        json.dump(filtered, out_file, indent=2)

    print(f"Saved {len(filtered)} record(s) to {output_file_path}.")

# Example usage
parse_log_file("logfile.txt", "filtered_records.txt")
