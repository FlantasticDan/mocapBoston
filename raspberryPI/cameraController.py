import time
import sys
import multiprocessing
from socket import gethostname
import pickle
import os
import picamera
import numpy as np
import cv2
import markerDetection as md

RESOLUTION = (1632, 1232)
FRAMERATE = 24
MAX_RECORDING = 15

class FrameBuffer(object):
    def __init__(self, resolution):
        self.buffer = []
        self.resolution = resolution
    
    def __iter__(self):
        self.iterationCount = -1
        return self
    
    def __next__(self):
        self.iterationCount += 1
        if self.iterationCount < self.frameCount:
            return self.iterationCount
        raise StopIteration

    def write(self, sensorOutput):
        self.buffer.append(sensorOutput)

    def flush(self):
        # Estabish Recording Length
        self.frameCount = len(self.buffer)
        print("Finished Recording : {}".format(self.frameCount))

        # Create Shared Memory Pool
        memoryStart = time.time()
        self.manager = multiprocessing.Manager()
        i, o = 0, 23
        self.pool = self.manager.list(self.buffer[i:o])
        del self.buffer[i:o]
        while len(self.buffer) > (o + 1):
            self.pool.extend(self.buffer[i:o])
            del self.buffer[i:o]
        self.pool.extend(self.buffer)
        del self.buffer
        memoryTime = time.time() - memoryStart
        print("Finished Creating Memory Pool : {}".format(memoryTime))
    
    def close(self):
        self.manager.shutdown()

def raw_resolution(splitter=False):
    """
    Round a (width, height) tuple up to the nearest multiple of 32 horizontally
    and 16 vertically (as this is what the Pi's camera module does for
    unencoded output).

    Originally Written by Dave Jones as part of PiCamera
    """
    width, height = RESOLUTION
    if splitter:
        fwidth = (width + 15) & ~15
    else:
        fwidth = (width + 31) & ~31
    fheight = (height + 15) & ~15
    return fwidth, fheight

def bytes2yuv(data):
    """
    Converts a bytes object containing YUV data to a `numpy`_ array.

    Originally Written by Dave Jones as part of PiCamera
    """
    width, height = RESOLUTION
    fwidth, fheight = raw_resolution()
    y_len = fwidth * fheight
    uv_len = (fwidth // 2) * (fheight // 2)
    if len(data) != (y_len + 2 * uv_len):
        raise PiCameraValueError(
            'Incorrect buffer length for resolution %dx%d' % (width, height))
    # Separate out the Y, U, and V values from the array
    a = np.frombuffer(data, dtype=np.uint8)
    Y = a[:y_len].reshape((fheight, fwidth))
    Uq = a[y_len:-uv_len].reshape((fheight // 2, fwidth // 2))
    Vq = a[-uv_len:].reshape((fheight // 2, fwidth // 2))
    # Reshape the values into two dimensions, and double the size of the
    # U and V values (which only have quarter resolution in YUV4:2:0)
    U = np.empty_like(Y)
    V = np.empty_like(Y)
    U[0::2, 0::2] = Uq
    U[0::2, 1::2] = Uq
    U[1::2, 0::2] = Uq
    U[1::2, 1::2] = Uq
    V[0::2, 0::2] = Vq
    V[0::2, 1::2] = Vq
    V[1::2, 0::2] = Vq
    V[1::2, 1::2] = Vq
    # Stack the channels together and crop to the actual resolution
    return np.dstack((Y, U, V))[:height, :width]

def yuv2rgb(yuv):
    """
    Originally Written by Dave Jones as part of PiCamera
    """
    # Apply the standard biases
    YUV = yuv.astype(float)
    YUV[:, :, 0]  = YUV[:, :, 0]  - 16  # Offset Y by 16
    YUV[:, :, 1:] = YUV[:, :, 1:] - 128 # Offset UV by 128
    # YUV conversion matrix from ITU-R BT.601 version (SDTV)
    #              Y       U       V
    M = np.array([[1.164,  0.000,  1.596],    # R
                [1.164, -0.392, -0.813],    # G
                [1.164,  2.017,  0.000]])   # B
    # Calculate the dot product with the matrix to produce RGB output,
    # clamp the results to byte range and convert to bytes
    rgb = YUV.dot(M.T).clip(0, 255).astype(np.uint8)
    return rgb

def buffer2bgr(frame):
    """Reads frame from the buffer and returns it as an openCV BGR Image."""
    yuvImage = bytes2yuv(frame)
    rgbImage = yuv2rgb(yuvImage)
    image = cv2.cvtColor(rgbImage, cv2.COLOR_RGB2BGR)
    return image

def findMarker(bufferIndex):
    """Multiprocessing Core for Marker Identification"""
    image = buffer2bgr(f.pool[bufferIndex])
    return md.markerID(image)

if __name__ == "__main__":
    print("Session ID")
    sessionID = input()

    # Camera Setup
    camera = picamera.PiCamera()
    camera.resolution = RESOLUTION
    camera.framerate = 24
    camera.iso = 1600
    camera.shutter_speed = 2000
    # camera.awb_mode = 'off'
    # camera.awb_gains = (1.5,1.5)
    
    f = FrameBuffer(RESOLUTION)

    # Establish Scyned Record Start
    print("Record Delay")
    recordDelay = float(input())
    time.sleep(recordDelay)

    # Recording
    camera.start_recording(f, 'yuv')
    try:
        camera.wait_recording(MAX_RECORDING)
        camera.stop_recording()
    except KeyboardInterrupt:
        camera.stop_recording()
    camera.close()

    # Time Tracking
    multiStart = time.time()

    # Multiprocessing
    pool = multiprocessing.Pool()
    mocap = pool.map(findMarker, f, chunksize=round(f.frameCount / 4))
    pool.close()
    f.close()

    # Report Time Tracking
    multiTime = time.time() - multiStart
    print("Multi Core Processing Finished : {}".format(multiTime))

    # Export Data
    host = gethostname()
    filename = "{}_{}.mocap".format(host, sessionID)

    with open(filename, "wb") as pik:
        pickle.dump(mocap, pik)
    print("Data Exported to : {}".format(os.path.join(os.getcwd(), filename)))




# ## DEBUG ##
# mocap = md.markerID(f.read(50))
# cv2.imwrite("nate.jpg", md.drawMarkerID(f.read(50), mocap))

# print("Finished Recording")
# process = time.time()
# mocap = []
# for i, _ in enumerate(f.buffer):
#     f.read(i)
# finish = time.time() - process
# print("Finished Single Core Processing in: {:3f} seconds.".format(finish))