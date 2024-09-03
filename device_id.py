def load_device_id():
    try:
        with open('/proc/cpuinfo', 'r') as file:
            for line in file:
                if line.startswith('Serial'):
                    device_id = line.split(':')[1].strip()
                    return device_id
        raise RuntimeError("Serial number not found in /proc/cpuinfo")
    except Exception as e:
        raise RuntimeError("Failed to load device ID") from e

# Call the function and print the result
device_id = load_device_id()
print(f"Device ID: {device_id}")

