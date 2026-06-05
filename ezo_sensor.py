"""
Generic helper class to handle Atlas Scientific EZO-based sensors

This uses subprocess to handle multiple-character commands as I couldn't figure out
the proper way to do non-command or offset SMBus-based I2C messages.
To that end it requires i2ctransfer which I believe is part of the I2C-tools package
e.g. apt install i2c-tools
"""
import time
import subprocess
from typing import Union
import binascii

class EzoSensor:
    """
    Atlas Scientific EZO sensors can use this class to manage their instances.
    """
      
    def i2c_send_cmd_get_resp(self, cmd:str) -> Union[bool, str]:
        """
        Uses subprocess.run to call i2ctransfer with the specified Atlas Scientific command. 
        Note that cmd must be hexified first.
        If the command fails or there is no device at the specified address False is returned.
        Otherwise the data-only portion of the response string is returned.    
        """
        
        # try:
        ret = subprocess.run(f'i2ctransfer -y 1 w1@{self.addr} {cmd}',
                             shell=True, capture_output=True)
        
        if ret.returncode != 0:
            return False

        time.sleep(1.0)

        ret = subprocess.run(f'i2ctransfer -y 1 r40@{self.addr}',
                             shell=True, capture_output=True, encoding="utf-8")

        if ret.returncode != 0:
            return False

        # Check that the first hex character is a 1 otherwise the command failed
        if ret.stdout[:4] != '0x01':
            # log.info(ret.stdout[0])
            return False

        # log.info(ret.stdout)
        # remove extraneous characters to prep for unhexlify-ing starting after the status char
        s = ret.stdout[4:]
        s = s.replace('0x00', '')
        s = s.replace('0x', '')
        s = s.replace(' ', '')
        s = s.replace('\n', '') 
        
        return binascii.unhexlify(s)
                
                
        # except Exception as e:
        #     log.error(e.with_traceback());
        #     return False
    
    def ping(self) -> bool:
        """
        Attempts to contact the ezo board using the info command. Returns True and sets
        the self.present flag if the ezo board responded 
        """
        if self.get_info() != False:
            self.present = True;
        else:
            # This isn't strictly necessary but we may want to use this as some kind of 
            # heartbeat if we find sensors dropping off the bus
            self.present = False;
            
        return self.present
    
    def get_info(self) -> Union[bool, str]:
        """
        Attempts to read the info string from the EZO board
        """        
        info = self.i2c_send_cmd_get_resp(hex(ord('i')))
        
        if info != False:
            # info is returned raw, for the data string we need to skip the first 3 characters 
            self.info = info[3:]
            # log.info(self.info)
             
        return info
            
    def get_reading( self, timeout:float=1.0 ) -> bool:
        """
        Attempts to trigger a sensor reading and stores the value read into 
        self.last_reading. 
        Returns True if a value was read or False otherwise
        """
        if self.present:
            ret = self.i2c_send_cmd_get_resp(hex(ord('R')))
            if ret != False:
                self.last_reading = float(ret)  
                return True 
        return False
    
    def send_cal(self, val=None, name=None):
        """
        Sends a 'cal' command to the EZO board. Some cals require an additional argument
        (such as ph low, mid, high), some require a value, and some require both. 
        These can be passed using the name and val arguments.
        """
        send_str = 'cal'
        if name != None:
            send_str = ',' + name
        
        if(val != None):
            send_str += ',' + val
        
        # TODO:
        print(send_str)
        
    def clear_cal(self):
        """
        Sends a 'cal,clear' command to the EZO board to remove any previous calibratino values.
        """
        # TODO
        pass
        
    def __init__(self, sensor_addr:int, sensor_name:str):
        self.present: bool = False
        self.addr:int = sensor_addr
        self.name:str = sensor_name
        self.info:str = ''
        self.last_reading:str = ''
