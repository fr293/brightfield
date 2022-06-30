# A command-line interface for the TTi power supply based current controller

import time
import power_supply_current_controller as pscc
import threading


def trigger_currents(connection_object, duration):
    pscc.switch_on(connection_object)
    time.sleep(duration)
    pscc.switch_off(connection_object)


def setup_timer(time_on):
    time.sleep(time_on)


def time_currents(config, amplitude, time_on, duration):
    setup_timer_thread = threading.Thread(name='setup_timer_thread', target=setup_timer, args=[time_on])
    setup_timer_thread.start()
    connection_object = pscc.open_controller()
    time.sleep(1)
    pscc.write_values(connection_object, config, amplitude)
    time.sleep(0.02)
    current_controller = threading.Thread(name='current_controller', target=trigger_currents,
                                          args=(connection_object, duration))
    setup_timer_thread.join()
    current_controller.start()
    current_controller.join()
    time.sleep(0.02)
    pscc.close_controller(connection_object)


def light_on():
    ps = pscc.open_controller()
    time.sleep(0.5)
    pscc.light_on(ps)
    time.sleep(0.5)
    pscc.close_controller(ps)
    time.sleep(0.5)


def light_off():
    ps = pscc.open_controller()
    time.sleep(0.5)
    pscc.light_off(ps)
    time.sleep(0.5)
    pscc.close_controller(ps)
    time.sleep(0.5)
    
