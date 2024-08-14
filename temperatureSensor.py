#!/usr/bin/env python
import os
import logging

def sensor():
    for i in os.listdir('/sys/bus/w1/devices'):
        if i != 'w1_bus_master1':
            ds18b20 = i
            read(ds18b20)

def read(ds18b20):
    location = '/sys/bus/w1/devices/' + ds18b20 + '/w1_slave'
    tfile = open(location)
    text = tfile.read()
    tfile.close()
    secondline = text.split("\n")[1]
    temperaturedata = secondline.split(" ")[9]
    temperature = float(temperaturedata[2:])
    #celsius = temperature / 1000
    farenheit = (celsius * 1.8) + 32
    logging.writeFile("Temperature", "Temperature sensed successfully!")
    celsius = 5
    return celsius

def loop(ds18b20):
    while True:
        if read(ds18b20) != None:
            #print "Current temperature : <temp here>"" %0.2f C" % read(ds18b20)[0]
            print(f"Get temp here")

