import numpy as np
from pyfiglet import Figlet
import time
import threading
from Tkinter import *
import tkFileDialog
import csv
from os.path import dirname
import brightfield_threaded as bt
import power_supply_current_controller_threaded as pscct
import heater as ht


# read in data from input csv, and program experiments
def main():
    f = Figlet(font='isometric1')
    print f.renderText('Ferg')
    time.sleep(1)
    g = Figlet(font='isometric3')
    print g.renderText('Labs')
    time.sleep(1)

    print('Welcome to the automated brightfield creep test tool.')
    time.sleep(0.5)

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    print('please select the file that contains details of the experiments to be run:')
    root.filename = tkFileDialog.askopenfilename(initialdir='C:/', title='Select file',
                                                 filetypes=(('csv files', '*.csv'), ('all files', '*.*')))
    if not root.filename:
        return False
    print('success: you have selected ' + root.filename)
    file_array = np.genfromtxt(root.filename, dtype=None, skip_header=1, delimiter=',', encoding=None)
    file_list = file_array.tolist()

    # print('please select the folder that you want the raw data to be saved in:')
    # root.directory = tkFileDialog.askdirectory(initialdir='C:/')
    # if not root.directory:
    #     return False
    # output_folder = root.directory + '/'
    # print('success: you have selected ' + output_folder)
    output_folder = dirname(root.filename) + '/'
    print('success: you have selected ' + output_folder)

    z_top = input("input the Z position of the top of the glass:")
    if z_top:  # Press enter if z info already registered
        z_focus = input('input the Z position of the bead (equally focused on both screens):')
        with open(output_folder + 'Z_information.csv', 'w+') as f:
            writer = csv.writer(f)
            writer.writerow([z_top, z_focus])

    print('success: starting experiment')

    pscct.light_on()
    heater = ht.start_temp()

    for experiment_run in file_list:
        # extract current configurations
        [filename, ca, cc, fon, fdur, num_frames, frame_period, temp] = experiment_run
        # filename=str(filename)[1:-1]
        filename = str(filename)

        ht.set_temp(heater, temp)

        c_thread = threading.Thread(name='c_thread', target=bt.multiframe,
                                    args=(num_frames, frame_period, output_folder, filename, heater))
        m_thread = threading.Thread(name='m_thread', target=pscct.time_currents, args=(cc, ca, fon, fdur))
        print('Performing experiment: ' + filename)
        c_thread.start()
        m_thread.start()
        c_thread.join()
        m_thread.join()
        time.sleep(10)

    ht.stop_temp(heater)
    pscct.light_off()

    return True


if __name__ == "__main__":
    main()
