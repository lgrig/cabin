import json
import io
import os
import time
from queue import Queue
from threading import Thread
from datetime import datetime
import logging
from PIL import Image
import picamera
import dropbox

#TO DO!
### SET A LIMIT ON IMAGES UNLESS MAJOR PIXEL CHANGES
### ADD LOGGING FOR NUMBER OF CHANGED PIXELS

# Motion detection settings:
# Threshold (how much a pixel has to change by to be marked as "changed")
# Sensitivity (how many changed pixels before capturing an image)
# ForceCapture (whether to force an image to be captured every forceCaptureTime seconds)
class CabinCamera():
    def __init__(self):

        self.config = json.load(open(os.path.dirname(os.path.realpath(__file__)) + '/.config.json'))
        self.threshold = 20

        #Note, test images are 100 * 75, 7500 pixels, sensitivty is in pixels
        self.sensitivity = 750
        self.force_capture = True
        # Hourly
        self.force_capture_time = 3600

        # File settings
        self.save_width = 1280
        self.save_height = 960
        self.disk_space_to_reserve = 40 * 1024 * 1024 # Keep 40 mb free on disk
        self.save_path = '/home/pi/development/python/cabin_camera/photos/'

        #camera settings
        self.camera = picamera.PiCamera()
        self.camera.start_preview()
        self.camera.resolution = (100, 75)
        self.last_capture = None

        #Remote Worker setup
        self.q = Queue()
        self.workers = 1
        #Logger setup
        logger_config = '/Users/Grignon/development/python/cabinpi/cabin_camera/logs/logging_config.json'
        logging.config.dictConfig(json.load(open(logger_config, 'rt')))

    # Capture a small test image (for motion detection)
    def capture_test_image(self):
        """Take a small shitty image to test compare pixels against"""
        stream = io.BytesIO()
        self.camera.capture(stream, format='bmp')
        stream.seek(0)
        img = Image.open(stream)
        buf_out = img.load()
        stream.close()
        return img, buf_out

    def save_full_image(self):
        """Save full sized image to disk, pass to dbx_upload_worker"""
        now = datetime.now()
        fmt = (now.year, now.month, now.day, now.hour, now.minute)
        filename = "capture-%04d%02d%02d-%02d%02d%02d.jpg" % (fmt)
        file_path = self.save_path + filename
        self.camera.resolution = (self.save_width, self.save_height)
        self.camera.capture(file_path)
        self.last_capture = time.time()
        self.q.put(file_path)

    ###NOTE THIS IS AN UNUSED FUNCTION AT THIS TIME###
    def keep_disk_space_free(self, bytes_to_reserve=None):
        """Delete files if not enough disk space until enough disk space"""
        def get_free_space():
            """Check current disk space"""
            return os.statvfs(".").f_bavail * os.statvfs(".").f_frsize
        logger = logging.getLogger('default')
        if get_free_space() < bytes_to_reserve:
            for filename in sorted(os.listdir(".")):
                if filename.startswith("capture") and filename.endswith(".jpg"):
                    os.remove(filename)
                    logger.warn("Not enough space: Deleted %s", filename)
                    if get_free_space() > bytes_to_reserve:
                        return

    def upload(self):
        """Upload files in folder to dropbox"""
        logger = logging.getLogger('default')
        dbx = dropbox.Dropbox(self.config['dropbox']['token'])
        #THIS SEEMS OUT OF PLACE, WHY INFINITY LOOP?
        #REMOVING INFINITY LOOP FOR NOW?
        #while True:
        filepath = self.q.get()
        with open(filepath, 'rb') as dbfile:
            dbx_path = "/photos/" + filepath.split("/")[-1]
            dbx.files_upload(dbfile.read(), dbx_path)
            os.remove(filepath)
        self.q.task_done()
        logger.info("uploaded to dbx: %s", dbx_path)
        return dbx_path

    def start_dbx_upload_worker(self):
        """Worker factory"""
        worker = Thread(target=self.upload, args=(self.q,))
        worker.setDaemon(True)
        worker.start()

    def check_force_capture(self):
        """T/F if it's been longer than the force capture time and if force capture is set"""
        return self.force_capture and time.time() - self.last_capture > self.force_capture_time

    def check_pixel_difference(self, buf_1, buf_2):
        """Identifies and counts pixel changes"""
        changed_pixels = 0
        changed_coords = []
        for x_coord in range(0, 100):
            for y_coord in range(0, 75):
                # Just check green channel as it's the highest quality channel
                pixdiff = abs(buf_1[x_coord, y_coord][1] - buf_2[x_coord, y_coord][1])
                if pixdiff > self.threshold:
                    changed_pixels += 1
                    changed_coords.append((x_coord, y_coord))
        return {'pix_diff': changed_pixels, 'changed_coords': changed_coords}

    def run(self):
        logger = logging.getLogger('default')
        retries = 0
        while retries <= 10:
            try:
                logger.info('starting camera')
                self.start_dbx_upload_worker()
                _, buffer1 = self.capture_test_image()
                self.last_capture = time.time()
                while True:
                    _, buffer2 = self.capture_test_image()
                    pix_diff = self.check_pixel_difference(buffer1, buffer2)['pix_diff']
                    force_capture = self.check_force_capture()
                    if pix_diff > self.sensitivity or force_capture:
                        self.save_full_image()
                        logger.info('force_capture: %s, pix_diff: %s', force_capture, pix_diff)
                    buffer1 = buffer2
            except BaseException as err:
                logger.error("retrying after failure: %s", err)
                retries += 1

if __name__ == '__main__':
    CabinCamera().run()
