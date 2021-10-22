# threaded version of the brightfield controller
# this has support for independent timed operation of the camera and magnet functions

import threading
import Queue
import time
import csv
import numpy as np
import imageio
import brightfield as b
from tqdm import tqdm
import cv2


def multiframe(number_of_frames, period, collated_filepath, collated_filename):
    pic_list = Queue.Queue()
    time_list = Queue.Queue()
    vimba_cam, camera_object, frame0 = b.open_camera()

    cv2.namedWindow('%s' % collated_filename, cv2.WINDOW_NORMAL)

    preview = [np.zeros((10, 10))]

    def actcam(pic_list, time_list, camera_object, frame0):
        exp_frame, pictime = b.takepic(camera_object, frame0)
        preview[0] = cv2.resize(exp_frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_CUBIC)
        pic_list.put(exp_frame)
        time_list.put(pictime)

    for i in tqdm(range(number_of_frames)):
        camera = threading.Thread(name='camera', target=actcam, args=(pic_list, time_list, camera_object, frame0))
        camera.start()
        time.sleep(period)
        camera.join()

        cv2.imshow('%s' % collated_filename, preview[0])
        cv2.waitKey(1)

    cv2.destroyAllWindows()

    b.close_camera(vimba_cam, camera_object)

    with imageio.get_writer(collated_filepath + collated_filename + '.tiff') as stack:
        with open(collated_filepath + collated_filename + '_time.csv', 'w+') as f:
            writer = csv.writer(f)
            while not pic_list.empty():
                pic = pic_list.get()
                stack.append_data(pic)
            while not time_list.empty():
                timepoint = time_list.get()
                writer.writerow([timepoint])
