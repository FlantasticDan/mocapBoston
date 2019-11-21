import time
import sys
import picamera
import numpy as np
import cv2

RESOLUTION = (1632, 1232)
FRAMERATE = 24
MAX_RECORDING = 35


class FrameBuffer(object):
    def __init__(self, resolution):
        self.buffer = []
        self.resolution = resolution
    
    def write(self, sensorOutput):
        self.buffer.append(sensorOutput)
    
    def flush(self):
        return None

    def raw_resolution(self, splitter=False):
        """
        Round a (width, height) tuple up to the nearest multiple of 32 horizontally
        and 16 vertically (as this is what the Pi's camera module does for
        unencoded output).

        Originally Written by Dave Jones as part of PiCamera
        """
        width, height = self.resolution
        if splitter:
            fwidth = (width + 15) & ~15
        else:
            fwidth = (width + 31) & ~31
        fheight = (height + 15) & ~15
        return fwidth, fheight

    def bytes2yuv(self, data):
        """
        Converts a bytes object containing YUV data to a `numpy`_ array.

        Originally Written by Dave Jones as part of PiCamera
        """
        width, height = self.resolution
        fwidth, fheight = self.raw_resolution()
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

    def yuv2rgb(self, yuv):
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
    
    def read(self, frame):
        """Reads frame from the buffer and returns it as an openCV BGR Image."""
        yuvImage = self.bytes2yuv(self.buffer[frame])
        rgbImage = self.yuv2rgb(yuvImage)
        image = cv2.cvtColor(rgbImage, cv2.COLOR_RGB2BGR)
        return image
        
# Camera Setup
camera = picamera.PiCamera()
camera.resolution = RESOLUTION
camera.framerate = 24

print("RECORDING")

f = FrameBuffer(RESOLUTION)
camera.start_recording(f, 'yuv')
recordStart = time.time()
try:
    camera.wait_recording(MAX_RECORDING)
    camera.stop_recording()
except KeyboardInterrupt:
    camera.stop_recording()

recordTime = time.time() - recordStart
print("Recorded {} frames over {:3f} seconds.".format(len(f.buffer), recordTime))