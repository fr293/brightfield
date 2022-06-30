# A command-line interface for the heater.py controller

import serial
import re
import time
import threading


# Start temperature control, wait for target to be reached
def start_temp():
    ht = HEATER()
    ht.starttempcont()
    return ht


def stop_temp(ht):
    ht.halttempcont()
    time.sleep(2)


def set_temp(ht, target_temperature):
    if ht.tempcont.isAlive():
        ht.tem = float(target_temperature)
        print('Target temperature set to %.1f C ...' % ht.tem)

        # Wait for temperature to be on target
        # True when 10 measurements are within +/- 1 degree
        # take one measurement per sec
        time.sleep(2)  # time for ont to come back to False if target changed
        while not ht.ont:  # if still not on target, wait
            print "Wait temperature... Current is %f" % ht.tempm
            time.sleep(2)
        print "Starting... Temperature is %f" % ht.tempm
    else:
        print('Error')
        return False


class HEATER:

    def __init__(self):
        # perform all the necessary actions for setting up
        # connect the serial ports and set up the arduino
        self.open_controller()
        # clear the startup string received from the arduino
        self.ard.readline()
        self.sendcfg()

    dbg = False
    smt = 20    # small move time in milliseconds; the time taken to make a small move on the stage
    frt = 25    # time between frames in milliseconds
    exp = 10    # camera exposure time in milliseconds
    tcr = ''    # temperature control board response
    htm = 0     # heater mode; 0 off, 1 cool, 2 heat
    hpw = 0     # heater power; 0-799
    fnm = 0     # fan mode; 0 off, 1 on
    tem = 17    # temperature set point in degrees C
    tempm = 20.0    # measured temperature in degrees C
    ttc = 1     # the period of the control loop in seconds
    tkp = 120   # proportional control constant for the temperature control module (heating mode)
    tkpc = 600  # proportional control constant for the temperature control module (cooling mode)
    tki = 1.5   # integral control constant for the temperature control module
    ers = 0     # total error for the heater controller
    ont = False  # boolean value indicating if the temperature controller is on target
    tcnt = 10    # counter temperature on target
    tst = False  # engage temperature step mode
    lgp = 1     # the logging period for temperature logging
    plp = 0.1   # the polling period for temperature polling
    slp = -4468.4   # slope parameter of stage distance to mirror DAC count relation
    setpos = 5.6
    off = 4095 - int(setpos * slp)  # offset parameter of stage distance to mirror DAC count relation
    stp = 6.0
    dst = 0.02
    frn = 5

    ard = serial.Serial()
    ard.baudrate = 115200
    ard.timeout = 5
    ard.port = 'COM3'

    data_in = threading.Event()
    tempcont = threading.Thread()
    tempcont_halt = threading.Event()
    temppoll = threading.Thread()
    temppoll_halt = threading.Event()
    seriallock = threading.Lock()

    def open_controller(self):
        if not self.ard.isOpen():
            try:
                # readline blocks further execution until the port is connected and the arduino responds
                self.ard.open()
                print('arduino connected')
            except serial.SerialException:
                raise UserWarning('could not connect to arduino')

    def close_ports(self):
        self.ard.close()

    # send and read configuration parameters ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def sendcfg(self):
        self.seriallock.acquire()
        self.ard.write(
            'SET {0} {1} {2} {3} {4} {5} {6} {7} {8} {9} \r'.format(
                str(self.htm),
                str(self.hpw),
                str(self.fnm),
                str(self.frn),
                str(self.frt),
                str(self.exp),
                str(self.stp),
                str(self.dst),
                str(self.slp),
                str(self.off)))
        self.seriallock.release()

    def readcfg(self):
        self.ard.flushInput()
        self.seriallock.acquire()
        self.ard.write('REP\r')
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        print(self.ard.readline())
        self.seriallock.release()

    # push heater.py parameters ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def sdh(self):
        self.seriallock.acquire()
        self.ard.write('STH\r')
        self.seriallock.release()

    # read heater.py parameters ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def rdh(self):
        self.ard.flushInput()
        self.seriallock.acquire()
        self.ard.write('RDH\r')
        self.seriallock.release()
        resp = self.ard.readline()
        if 'END' in resp:
            return resp
        else:
            print('temperature poll error')
            time.sleep(0.1)
            return False

    # read heater.py parameters and control temperature~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def clt(self):

        # count is the number of polling periods that the bath must within +- 1 degree of the set point to be on
        # target
        # maxsig is the maximum signal that can be sent to the temperature driver board coolingfactor is the
        # proportion of maximum power that can be applied in cooling mode

        maxsig = 799
        coolingfactor = 0.75

        maxers = maxsig / self.tki

        # extract measured temperature from readout we may want to refactor the extraction as a function that takes a
        # keyword and a string, and returns the value of the argument after it, though given that we're dealing with
        # mixed data types, this might be more difficult than it is useful paramstring = "$HC,MODE,1,PWM,400,TEMP,
        # 26.5,END"

        paramstring = self.tcr
        kwtemp = [match.start() for match in re.finditer(re.escape('TEMP'), paramstring)]
        delimiters = [match.start() for match in re.finditer(re.escape(','), paramstring)]
        position = filter(lambda x: x >= kwtemp[0], delimiters)
        position = position[0:2]
        position[0] = position[0] + 1
        tempstring = paramstring[position[0]:position[1]]
        if "." in tempstring:
            self.tempm = float(tempstring)
        else:
            self.tempm = int(tempstring)

        # calculate the error and set the parameters
        temperror = self.tem - self.tempm

        # this block checks to see if the controller is on target by checking if the temperature has gone out of
        # range recently
        if abs(temperror) <= 1:  # +/- 1 degrees Celsius
            self.tcnt = self.tcnt - 1
            if self.tcnt <= 0:
                self.tcnt = 1
                self.ont = True
        else:
            self.tcnt = 10 # outside desired +-1 range,
            self.ont = False

        # block to prevent integrator wind-up
        if abs(temperror) < 8:
            self.ers = self.ers + (temperror * self.ttc)
        else:
            self.ers = 0

        if self.ers > maxers:  # limit max and minimum signals
            self.ers = maxers
        elif self.ers < 0:
            self.ers = 0

        if self.tst:
            signal = 500
        elif temperror < 0:
            signal = (temperror * self.tkpc) + (self.ers * self.tki)  # current is greater than target, cool down
        else:
            # signal = (temperror * self.tkp) + (self.ers * self.tki)  # current is smaller than target, heat up
            signal = (temperror * 200) + (self.ers * self.tki)  # original = 120

        if signal > maxsig:
            signal = maxsig
        elif signal < -(maxsig * coolingfactor):
            signal = -(maxsig * coolingfactor)

        self.hpw = abs(signal)

        if signal >= 0:
            self.htm = 2
            self.fnm = 0

        else:
            self.htm = 1
            self.fnm = 1

        if self.dbg:
            print('demand temperature: ' + str(self.tem) + ', ' + 'measured temperature: ' + str(self.tempm))
            print('proportional signal: ' + str(temperror * self.tkp) + ', ' + 'integral signal: '
                  + str((self.ers * self.tki)))
            print('signal: ' + str(signal) + ', ' + 'heater.py power: ' + str(self.hpw) + ', ' + 'heater.py mode: ' +
                  str(self.htm))
            if self.ont:
                print('on target')

        # set the peltier duty cycle and throttle down to the maximum set above

        # send the parameters and push to the heater.py
        self.sendcfg()
        self.sdh()

    # run temperature control ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def acttempcont(self):
        if not self.temppoll.isAlive():
            self.starttemppoll()

        while not self.temppoll.isAlive() and self.data_in.isSet():
            print('waiting for temperature controller')
            time.sleep(0.5)

        print('temperature controller running')
        self.tempcont_halt.clear()
        while not self.tempcont_halt.isSet():
            if self.data_in.isSet():
                self.clt()
            time.sleep(self.ttc)

    def starttempcont(self):
        if self.tempcont.isAlive():
            print('warning: thread already running')
        else:
            self.ers = 0
            self.tempcont = threading.Thread(name='tempcont', target=self.acttempcont)
            self.tempcont.start()

    def halttempcont(self):
        if not self.tempcont.isAlive():
            print('warning: temperature control not running')
        else:
            if not self.tempcont_halt.isSet():
                self.tempcont_halt.set()
                print('temperature control halted')
            else:
                print('warning: flag not set')

        # shut the heater.py controller down
        self.htm = 0
        self.fnm = 0
        self.sendcfg()
        self.sdh()
        self.temppoll_halt.set()

    # poll temperature control board ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def acttemppoll(self):
        self.data_in.clear()
        if not self.ard.isOpen():
            print('warning: port is not open')
            print('attempting to open')
            try:
                self.open_controller()
                print('ports opened successfully')
            except UserWarning:
                print('ports unreachable, releasing thread locks in 2 seconds')
                time.sleep(2)
                self.seriallock.release()
                return

        self.temppoll_halt.clear()
        while not self.temppoll_halt.isSet():
            read = self.rdh()
            if read:
                self.tcr = read
                self.data_in.set()
            else:
                self.data_in.clear()
            time.sleep(self.plp)

    def starttemppoll(self):
        if self.temppoll.isAlive():
            print('warning: thread already running')
        else:
            self.temppoll = threading.Thread(name='temppoll', target=self.acttemppoll)

            self.temppoll.start()

    def halttemppoll(self):
        if self.temppoll.isAlive():
            if not self.temppoll_halt.isSet():
                self.temppoll_halt.set()
                print('temperature polling halted')
            else:
                print('warning: flag not set')
        else:
            print('warning: temperature polling not running')
            
