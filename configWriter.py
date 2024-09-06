from configparser import ConfigParser

def createConfig():
    config = ConfigParser()

    config["SECRETS"] = {
        "apiURL": "https://water-watch-58265eebffd9.herokuapp.com/upload/",
        "apiKey": "12345abcde",
        "AccountNumber": "abcde"
    }

    config["GENERAL"] = {
        "sleepInterval": 5,
        "MaxFileSize": 50,
        "TrimPercent": 0.10
    }


    with open("waterMonitor.ini", "w") as f:
        config.write(f)