def load_device_id():
    try:
        with open('/etc/device_id.conf', 'r') as file:
            device_id = file.read().strip()
        return device_id
    except Exception as e:
        raise RuntimeError("Failed to load device ID") from e
