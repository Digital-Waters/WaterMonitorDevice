#!/bin/bash

#
# This script is meant to be run either as a cron job or from a systemd timer.
# Ensures the wifi radio is on.
#

radio_on () {
    if [[ $(nmcli radio wifi) == "enabled" ]]; then
        echo 1
    else
        echo 0
    fi
}

# If the radio is off, turn it on
if [[ $( radio_on ) == "0" ]]; then
    nmcli radio wifi on
fi
