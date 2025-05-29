#!/bin/bash

# 
# This script is meant to be run either as a cron job or from a systemd timer.
# If there is an existing, active connection then there is no change to that connection.
# If the radio was off, it is turned on and we wait NUM_SEC_FOR_CONNECTION seconds
# If there is a connection after that time then we are done.
# If there is no connection then we assume that there is no AP in range, and turn 
#  off the radio to save power.
#



NUM_SEC_FOR_CONNECTION=5

radio_on () {
    if [[ $(nmcli radio wifi) == "enabled" ]]; then
        echo 1 
    else
        echo 0
    fi
}

connected () {
    nmcli device | awk '{if ($2 == "wifi") { if ($3 !~ "dis") {print 1;} else {print 0;}}}'
}

# Check the radio status
if [[ $( radio_on ) == "0" ]]; then
    # if the radio is off, turn it on and wait a bit for a connection
    nmcli radio wifi on
    sleep $NUM_SEC_FOR_CONNECTION
fi

# Check to see if we are connected
if [[ $( connected ) == "0" ]]; then
    # There is no connction so turn the radio off unti the next cycle
    nmcli radio wifi off
fi

# Else there is a connection and we quit silently until the next cycle

