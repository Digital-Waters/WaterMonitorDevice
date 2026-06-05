"""
Command-Line Calibration tool for Atlas Scientific probes via EZO carrier boards

Use this tool to calibrate Atlas Scientific probes connected to EZO carrier boards.
This is a Linux-based tool and is not tested on Windows or Mac machines. It is intended
to be run on a Raspberry Pi with the sensors attached to I2C bus 1, though this can be
configured TBD 

Note that this tool uses I2C to query the devices. EZO devices must be placed into I2C mode 
separately. See the Atlas Scientific documentation for more information.
 
"""
import cmd, sys, time, select
from ezo_sensor import EzoSensor
from certifi.__main__ import args
 
PRB_DO  = 0x61
PRB_ORP = 0x62
PRB_PH  = 0x63
PRB_EC  = 0x64
PRB_RTD = 0x66
 
# This should probably comme from a config file or ?
AS_SENSOR_INFO = [
    {'addr':PRB_DO, 'name':'sensor_do'},
    # {'addr':PRB_ORP, 'name':'sensor_orp'},
    # {'addr':PRB_PH, 'name':'sensor_ph'},
    {'addr':PRB_EC, 'name':'sensor_conductivity'},
    # {'addr':PRB_RTD, 'name':'temperature'}
]
 
 
log = None

as_sensors = {}
 
# found this here https://techdevops.wordpress.com/2015/03/24/non-blocking-io-keyboard-listener-in-python/
def check_keypress_nb() -> bool:
    # while True:
    kin = select.select([sys.stdin], [], [], 1)[0]
    if kin:
        value = sys.stdin.readline().rstrip()
        return True
 
        
        # if (value == "q"):
        #     print ("Exiting")
        #     sys.exit(0)
        # else:
        #     print ("You entered: %s" % value)
    else:
        return False
        # processSomething()
    
     
 
 
class AsCalShell(cmd.Cmd):
    intro = 'Digital Waters calibration tool for Atlas Scientific devices.\n Type help or ? for commands.\n'
    prompt = '$ '
    file = None
    
    def probe_present(self, probe) -> bool:
        if not probe in as_sensors.keys():
            print('EZO board not detected.')
            return False
        return True

    def prompt_yn(self, prompt) -> bool:
        '''
        Prompts the user for a yes / no input. Returns True for Yes and False for No
        '''
        print(prompt)
        yn = input()
        if yn.upper() != 'Y' :
            return False
        return True
    
    def prompt_val(self, prompt):
        '''
        Prompts the user for a numeric value. If no input is given then None is returned.
        '''
        print(prompt)
        try:
            val = float(input())
        except ValueError as ve:
            return None
        
        return val

    def cond_get_k(self, arg) -> float:
        '''
        Parses arg to get the floating point K value. Returns 1.0 if there are any errors or
        by default. 
        '''
        if arg:
            try:
                k = float(arg)
                # We could check for k=1.0 here, but might as well just send it
                # regardless (e.g. if the user swaps a 10.0 for a 1.0 we'll need
                # to let the EZO board know anyway
                
                #TODO: Send the K command
                
            except ValueError as ve:
                k = 1.0
        else:
            k = 1.0
            
        print(f'Calibrating with K = {k}')
        return k


    # ---- Command List ----
    def do_test(self, arg):
        'Test command'
        print(arg)
        
    def do_list(self, arg):
        'Probe and list the available AS EZO boards'
        # check each AS sensor to see if it is installed and responding
        for addr, sensor in as_sensors.items():
            if sensor.present:
                print(f'0x{addr:02X}: Atlas Scientific {sensor.name} detected: {sensor.info}')
                
        pass
    def do_read(self, arg):
        'Continuously read the probe specified by its address'
        addr = int(arg, 16)
        
    def do_cal_do(self, arg):
        'Calibrate Dissolved Oxygen'
        
        if not self.probe_present(PRB_DO):
            return
        
        print('Requirements: Galvanic DO probe, Zero Dissolved Oxygen calibration solution')
        
        print('Step 1:')
        print('- Prepare Zero Dissolved Oxygen Solution.')
        print('- Insert probe and swirl it to remove any trapped air bubbles.')
        print('- Wait until reading settles to 0.0 or 4 hours, whichever comes first.')
        print('  * Note that for DO probes with fresh electrolyte this step may take several up to as much as 12 hours.')
        
        ts = time.time()

        last_val = 0.0
        while not check_keypress_nb():
            if as_sensors[PRB_DO].get_reading():
                diff = as_sensors[PRB_DO].last_reading - last_val
                print(f'reading: {as_sensors[0x61].last_reading} ; diff:{diff}... Press \'Enter\' to continue', end='\r')
                last_val = as_sensors[PRB_DO].last_reading 
        
        elapse_time = time.time() - ts
        
        if not self.prompt_yn(f'Did either the settings stabilize to 0 or was time limit exceeded ({elapse_time:0.2f}s? (y/N)'):
            print("Canceling")
            return
        
        # TODO: Send 0 point cal:
        as_sensors[PRB_DO].send_cal(val='0')
        
        print('Step 2:')
        print('- Remove probe from solution and gently dry it.')
        print('- Wait until readings settle.')

        ts = time.time()

        last_val = 0.0
        while not check_keypress_nb():
            if as_sensors[PRB_DO].get_reading():
                diff = as_sensors[PRB_DO].last_reading - last_val
                print(f'reading: {as_sensors[0x61].last_reading} ; diff:{diff}... Press \'Enter\' to continue', end='\r')
                last_val = as_sensors[PRB_DO].last_reading 

        elapse_time = time.time() - ts

        if not self.prompt_yn(f'Did either the settings stabilize or was time limit exceeded {elapse_time :0.2f}s ? (y/N)'):
            print("Canceling")
            return

        # TODO: write the cal command
        as_sensors[PRB_DO].send_cal()

            
        print('Basic dissolved oxygen calibration complete. Run cal_do_adv for advanced temperature calibration.')

    def do_cal_do_adv(self, arg):
        'Advanced calibration of DO sensors. Make sure to run cal_do first.'
        if not self.probe_present(PRB_DO):
            return
        
        print('Handle temperature compensation calibration for Dissolved Oxygen sensors.')
        print('Not yet supported. ')

    def do_cal_ec2(self, arg):
        '2-point Conductivity Calibration. K=1.0 assumed unless specified.'
        
        if not self.probe_present(PRB_EC):
            return

        k = self.cond_get_k(arg)
        
        print('Step 1, Preparation:')
        print('- Prepare conductivity solution. Allow the solution to reach ambient temperature and record this temperature.')
        print('- Using the temperature compensation table that came with your calibration solution, record the expected EC at the given temperature.')
        print('Step 2, Dry calibration:')
        print('- If your EC probe is not dry, gently wipe or blow it dry using compressed air.')
        print('- When the readings settle, press "Enter" to continue')

        ts = time.time()
        while not check_keypress_nb():
            if as_sensors[PRB_EC].get_reading():
                print(f'{as_sensors[PRB_EC].last_reading} ... Press \'Enter\' to continue', end='\r')
        
        elapse_time = time.time() - ts
        if not self.prompt_yn(f'Did either the settings stabilize or was time limit exceeded ({elapse_time :0.2f}s elapsed) ? (y/N)'):
            print("Canceling")
            return
        

        # TODO: Send dry cal command
        
        print('Step 3, Wet Calibration')
        print('- Place the EC probe in the calibration solution from Step 1')
        print('- Shake the probe as to release any trapped air bubbles.')
        print('- Wait until the readings stabilize. They should be within +/- 40% of the value recorded in Step 1')
        ts = time.time()
        while not check_keypress_nb():
            if as_sensors[PRB_EC].get_reading():
                print(f'{as_sensors[PRB_EC].last_reading} ... Press \'Enter\' to continue', end='\r')
        
        if not self.prompt_yn(f'Did either the settings stabilize or was time limit exceeded ({elapse_time :0.2f}s elapsed)? (y/N)'):
            print("Canceling")
            return

        val = self.prompt_val('Enter the expected temperature compensated value (recorded in Step 1)')
        
        if val:
            # TODO: Send the wet cal value
            
            print('EC calibration Complete.')
            pass
        
        print('Value not recognzed, cancelling.')
        
        
    def do_cal_ec3(self, arg):
        '3-point Conductivity Calibration. K=1.0 assumed unless specified.'

        if not self.probe_present(PRB_EC):
            return
        
        k = self.cond_get_k(arg)
        
        print('Step 1, Preparation:')
        print('- Prepare conductivity solutions. Allow the solutions to reach ambient temperature and record this temperature.')
        print('- Using the temperature compensation table that came with your calibration solutions, record both expected EC values at the given temperature.')
        print('Step 2, Dry calibration:')
        print('- If your EC probe is not dry, gently wipe or blow it dry using compressed air.')
        print('- When the readings settle, press "Enter" to continue')

        ts = time.time()
        while not check_keypress_nb():
            if as_sensors[PRB_EC].get_reading():
                print(f'{as_sensors[PRB_EC].last_reading} ... Press \'Enter\' to continue', end='\r')
        
        elapse_time = time.time() - ts
        if not self.prompt_yn(f'Did either the settings stabilize or was time limit exceeded ({elapse_time :0.2f}s elapsed)? (y/N)'):
            print("Canceling")
            return
        

        # TODO: Send dry cal command
        
        print('Step 3, Wet Calibration')
        print('- Place the EC probe in the calibration solution from Step 1')
        print('- Shake the probe as to release any trapped air bubbles.')
        print('- Wait until the readings stabilize. They should be within +/- 40% of the value recorded in Step 1')
        ts = time.time()
        while not check_keypress_nb():
            if as_sensors[PRB_EC].get_reading():
                print(f'{as_sensors[PRB_EC].last_reading} ... Press \'Enter\' to continue', end='\r')
        
        if not self.prompt_yn(f'Did either the settings stabilize or was time limit exceeded ({elapse_time :0.2f}s elapsed)? (y/N)'):
            print("Canceling")
            return

        val = self.prompt_val('Enter the expected temperature compensated value (recorded in Step 1)')
        
        if val:
            # TODO: Send the wet cal value
            
            print('EC calibration Complete.')
            pass
        
        print('Value not recognzed, cancelling.')    
            
            
    def do_cal_orp(self, arg):
        'Calibrate ORP probe'
        if not self.probe_present(PRB_ORP):
            return
        
        
        
    def do_cal_ph(self, arg):
        'Calibrate pH probe'
        if not self.probe_present(PRB_PH):
            return
        
        

if __name__ == "__main__":
    
    # Instantiate all the ezo sensors listed in AS_SENSOR_INFO list     
    for i in AS_SENSOR_INFO: 
        as_sensors[i['addr']] = EzoSensor(i['addr'], i['name'])
    
    print(f'Probing attached sensors')
    for addr, sensor in as_sensors.items():
        if sensor.ping():
            print(f'0x{sensor.addr:02X}: Atlas Scientific {sensor.name} detected: {sensor.info}')

    AsCalShell().cmdloop()
