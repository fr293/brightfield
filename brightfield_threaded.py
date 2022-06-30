# threaded version of the brightfield controller
# this has support for independent timed operation of the camera and magnet functions

import threading
import Queue
import time
import csv
import imageio
import brightfield as b
from tqdm import tqdm
import cv2


def actcam(pic_list, time_list, preview_list, camera_object, frame0):
    exp_frame, pictime = b.takepic(camera_object, frame0)
    preview = cv2.resize(exp_frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_CUBIC)
    preview_list.put(preview)
    pic_list.put(exp_frame)
    time_list.put(pictime)


def savecam(number_of_frames, pic_list, time_list, temp_list, collated_filepath, collated_filename):
    with imageio.get_writer(collated_filepath + collated_filename + '.tiff') as stack:
        with open(collated_filepath + collated_filename + '_time.csv', 'w+') as f:
            writer = csv.writer(f)
            for frame in range(number_of_frames):
                pic = pic_list.get()
                stack.append_data(pic)
                timepoint = time_list.get()
                current_temp = temp_list.get()
                writer.writerow([timepoint, current_temp])


def multiframe(number_of_frames, period, collated_filepath, collated_filename, heater):
    pic_list = Queue.Queue()
    time_list = Queue.Queue()
    temp_list = Queue.Queue()
    preview_list = Queue.Queue()
    vimba_cam, camera_object, frame0 = b.open_camera()
    cv2.namedWindow('%s' % collated_filename, cv2.WINDOW_NORMAL)

    # Save frames during acquisition
    save = threading.Thread(name='save', target=savecam,
                            args=(number_of_frames, pic_list, time_list, temp_list, collated_filepath, collated_filename))
    save.start()

    for i in tqdm(range(number_of_frames)):
        start_time = time.time()
        temp_list.put(heater.tempm)
        camera = threading.Thread(name='camera', target=actcam,
                                  args=(pic_list, time_list, preview_list, camera_object, frame0))
        camera.start()
        camera.join()

        preview = preview_list.get()
        cv2.imshow('%s' % collated_filename, preview)
        cv2.waitKey(1)

        delay = period + start_time - time.time()
        if delay < 0:
            delay = 0
        time.sleep(delay)

    save.join()
    cv2.destroyAllWindows()
    b.close_camera(vimba_cam, camera_object)
