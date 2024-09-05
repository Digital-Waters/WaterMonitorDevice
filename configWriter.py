from configparser import ConfigParser

config = ConfigParser()

config["SECRETS"] = {
    "apiURL": "https://water-watch-58265eebffd9.herokuapp.com/upload/",
    "apiKey": "12345abcde",
    "AccountNumber": "abcde"
}

config["GENERAL"] = {
    "sleepInterval": 5,
    "timeZone": "America/Toronto",
    "MaxFileSize": 50,
    "TrimPercent": 0.10
}

config["SENSORS"] = {
    "camera": "on",
    "GPS": "on",
    "temp": "on",
    "PH": "off",
    "O2": "off",
    "conductivity": "off",
    "terpidity": "off"
}

with open("waterMonitor.ini", "w") as f:
    config.write(f)