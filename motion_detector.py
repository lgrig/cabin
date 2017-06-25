import json
import io
import subprocess
import os
import time
import dropbox
from datetime import datetime
from PIL import Image
import picamera

from queue import Queue
from threading import Thread

# Motion detection settings:
# Threshold (how much a pixel has to change by to be marked as "changed")
# Sensitivity (how many changed pixels before capturing an image)
# ForceCapture (whether to force an image to be captured every forceCaptureTime seconds)
class CabinCamera():
    def __init__(self):
        self.threshold = 20
        self.sensitivity = 30
        self.forceCapture = True
        self.forceCaptureTime = 60 * 60 # Once an hour

        # File settings
        self.saveWidth = 1280
        self.saveHeight = 960
        self.diskSpaceToReserve = 40 * 1024 * 1024 # Keep 40 mb free on disk
        self.camera = picamera.PiCamera()
        self.camera.start_preview()
        self.camera.resolution = (100, 75)
        self.q = Queue()
        self.workers = 1

    # Capture a small test image (for motion detection)
    def captureTestImage(self, camera):
        #print("capturing test image")
        stream = io.BytesIO()
        camera.capture(stream, format= 'bmp')
        stream.seek(0)
        im = Image.open(stream)
        buffer = im.load()
        stream.close()
        #print("I have it!")
        return im, buffer

    # Save a full size image to disk
    def saveImage(self, diskSpaceToReserve, camera):
        time = datetime.now()
        filename = "capture-%04d%02d%02d-%02d%02d%02d.jpg" % (time.year, time.month, time.day, time.hour, time.minute, time.second)
        filepath = '/home/pi/development/python/cabin_camera/photos/' + filename
        camera.resolution = (1296, 972)
        camera.capture(filepath)
        self.q.put(filepath)

    # Keep free space above given level
    def keepDiskSpaceFree(self, bytesToReserve):
        if (self.getFreeSpace() < bytesToReserve):
            for filename in sorted(os.listdir(".")):
                if filename.startswith("capture") and filename.endswith(".jpg"):
                    os.remove(filename)
                    print("Deleted %s to avoid filling disk" % filename)
                    if (self.getFreeSpace() > bytesToReserve):
                        return

    # Get available disk space
    def getFreeSpace(self):
        st = os.statvfs(".")
        du = st.f_bavail * st.f_frsize
        return du

    def upload(self, q):
        dbx = dropbox.Dropbox(json.load(open(os.path.dirname(os.path.realpath(__file__)) + '/.config.json'))['dropbox']['token'])
        while True:
            filepath = q.get()
            with open(filepath, 'rb') as f:
                print("I've got a file!")
                dbx_path = "/photos/" + filepath.split("/")[-1]
                print(dbx_path)
                dbx.files_upload(f.read(), dbx_path)
                print("I just uploaded that file!")
            try:
                os.remove(filepath)
                print("I deleted the local file")
            except os.FileNotFoundError:
                pass
            q.task_done()
            print("all done")

    def run(self):
        worker = Thread(target=self.upload, args=(self.q,))
        worker.setDaemon(True)
        worker.start()
        #print("I am running")
        # Get first image
        image1, buffer1 = self.captureTestImage(self.camera)
        # Reset last capture time
        lastCapture = time.time()
        #print("I took a picture at " + str(lastCapture))
        # Get comparison image
        #print("I am comparing")
        while (True):
            image2, buffer2 = self.captureTestImage(self.camera)
            # Count changed pixels
            changedPixels = 0
            for x in range(0, 100):
                for y in range(0, 75):
                    # Just check green channel as it's the highest quality channel
                    pixdiff = abs(buffer1[x,y][1] - buffer2[x,y][1])
                    if pixdiff > self.threshold:
                        changedPixels += 1

            # Check force capture
            if self.forceCapture:
                if time.time() - lastCapture > self.forceCaptureTime:
                    changedPixels = self.sensitivity + 1

            # Save an image if pixels changed
            if changedPixels > self.sensitivity:
                lastCapture = time.time()
                self.saveImage(self.diskSpaceToReserve, self.camera)

            # Swap comparison buffers
            image1 = image2
            buffer1 = buffer2

if __name__ == '__main__':
    CabinCamera().run()
