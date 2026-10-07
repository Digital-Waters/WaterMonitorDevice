from configparser import ConfigParser

def createConfig():
    config = ConfigParser()

    config["SECRETS"] = {
        "apiURL": "https://water-watch-58265eebffd9.herokuapp.com/upload/",
        "apiKey": "12345abcde",
        "statusURL": "https://api.digitalwaters.org/api/v1/devices/status",  # blank disables status reporting
        "AccountNumber": "abcde"
    }

    config["GENERAL"] = {
        "sleepInterval": 5,
        "LogMaxFileSizeMB": 5,
        "LogFileCount": 20
    }


    with open("waterMonitor.ini", "w") as f:
        config.write(f)