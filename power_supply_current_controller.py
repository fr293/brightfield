# A command-line interface for the TTi power supply based current controller

import serial
import random
import time
import numpy as np
import threading

seriallock = threading.Lock()

def open_controller():
    try:
        ps = serial.Serial('COM4', 19200, timeout=0.05)
        print "Connection to Current Controller Successful"
        return ps
    except serial.SerialException:
        print('Error: Could not connect to Current Controller')


def close_controller(connection_object):
    connection_object.close()


def write_values(connection_object, config, amplitude):
    supply = range(1, 5)
    random.shuffle(supply)

    current_configs = np.array([[0, 1, 1, 0],
                                [0.5, 0.5, 1, 1],
                                [1, 1, 0.5, 0.5],
                                [1, 0, 0, 1],
                                [-1, -1, 1, 1],
                                [1, -1, -1, 1]])

    current_amplitudes = np.array([0.5, 1, 1.5, 2, 2.5, 0.1, 0.2, 0.3, 0.4])

    current_values = current_amplitudes[amplitude - 1] * current_configs[config - 1]
    current_values[current_values == 0] = 0.001

    seriallock.acquire()
    for i in supply:
        connection_object.write('PW ' + str(i) + ' ' + str(current_values[i - 1]) + '\r\n')
        time.sleep(0.02)
    seriallock.release()


def switch_on(connection_object):
    seriallock.acquire()
    connection_object.write('P_ON\r\n')
    seriallock.release()


def switch_off(connection_object):
    seriallock.acquire()
    connection_object.write('P_OFF\r\n')
    seriallock.release()


def light_on(connection_object):
    seriallock.acquire()
    connection_object.write('Light_ON' + '\r\n')
    seriallock.release()


def light_off(connection_object):
    seriallock.acquire()
    connection_object.write('Light_OFF' + '\r\n')
    seriallock.release()
