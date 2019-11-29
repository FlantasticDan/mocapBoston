import paramiko
import time
import random
import pickle
import os

IP = ["192.168.1.113"]
HOST = ["blueTriangle"]
STORAGE = "F:/mocapMath/Sandbox/rpi"
# IP = ("10.10.10.2", "10.10.10.3", "10.10.10.4", "10.10.10.5")

RESOLUTION = (1632, 1232)
FRAMERATE = 24
MAX_RECORDING = 15
ISO = 1600
SHUTTER_SPEED = 2000
AWB_MODE = 'auto'
AWB_GAINS = (1.5, 1.5)

def generateSession():
    """Generates a Random 4 Digit Hex"""
    randomInt = random.randint(4096, 65535)
    hexInt = format(randomInt, 'X')
    return hexInt

class remoteCamera():
    def __init__(self, ipAdress, still=False):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ipAdress, username="pi", password="mocapMath")

        if not still:
            self.i, self.o, self.e = self.ssh.exec_command("cd /home/pi/Documents; python3 cameraController.py")
        else:
            self.i, self.o, self.e = self.ssh.exec_command("cd /home/pi/Documents; python3 cameraController_Still.py")

    def hold(self, checksum):
        """Hold execution until remote camera returns the checksum string."""
        check = self.o.readline()

        # Refuse Empty Lines
        while check == '\n':
            check = self.o.readline()

        check = check.rstrip()
        if check == checksum:
            return True
        else:
            raise Exception
    
    def get(self):
        """Get printout from remote camera and return the value after ' : '."""
        payload = self.o.readline()
    
        # Refuse Empty Lines
        while payload == '\n':
            payload = self.o.readline()
        
        payload = payload.rstrip()
        payload = payload.split(" : ")
        return payload[1]
    
    def send(self, payload):
        """Send payload as input string to remote client."""
        self.i.write("{}\n".format(payload))
        self.i.flush()
    
    def getFile(self, remotepath, localpath):
        """Get file from remote client at remotepath and store it at localpath."""
        sftp = self.ssh.open_sftp()
        sftp.get(remotepath, localpath)

def remoteCapture(sessionID, still=False):
    """Triggers remote capture and processing on connected hosts."""

    # Establish Connections
    CAMERAS = []
    for client in IP:
        connection = remoteCamera(client, still)
        connection.hold("Session ID")
        connection.send(sessionID)
        connection.hold("Resolution")
        connection.send(RESOLUTION[0])
        connection.send(RESOLUTION[1])
        connection.hold("Frame Rate")
        connection.send(FRAMERATE)
        connection.hold("Max Recording")
        connection.send(MAX_RECORDING)
        connection.hold("ISO")
        connection.send(ISO)
        connection.hold("Shutter Speed")
        connection.send(SHUTTER_SPEED)
        connection.hold("AWB Mode")
        connection.send(AWB_MODE)
        connection.hold("AWB Gains")
        connection.send(AWB_GAINS[0])
        connection.send(AWB_GAINS[1])
        CAMERAS.append(connection)

    # Prepare to Start Recording
    for camera in CAMERAS:
        camera.hold("Record Delay")

    # Sync Camera Record Starts
    timeUntilStart = 1
    timeBase = time.time()
    for camera in CAMERAS:
        camera.send(str(timeUntilStart - (time.time() - timeBase)))
    holdTime = timeUntilStart - (time.time() - timeBase)
    time.sleep(holdTime)
    print("Recording Started on Remote Cameras")

    # Get Telemetry
    for i, camera in enumerate(CAMERAS):
        print("Recorded {} Frames on {}".format(camera.get(), HOST[i]))
    for i, camera in enumerate(CAMERAS):
        print("Allocated Shared Memory in {} seconds on {}".format(camera.get(), HOST[i]))
    for i, camera in enumerate(CAMERAS):
        print("Multi Core Processing Completed in {} seconds on {}".format(camera.get(), HOST[i]))

    # Retrieve Data
    os.mkdir(os.path.join(STORAGE, sessionID))
    workspace = os.path.join(STORAGE, sessionID)
    for camera in CAMERAS:
        dataPath = camera.get()
        dataFile = os.path.basename(dataPath)
        dataLocal = os.path.join(workspace, dataFile)
        camera.getFile(dataPath, dataLocal)
        print("Recieved {}".format(dataFile))
    
    return workspace

if __name__ == "__main__":
    remoteCapture(generateSession())
