import paramiko
import time
import random
import pickle
import os
import threading

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
            print(self.e.readlines())
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

def remoteCapture(sessionID, gui, still=False, ip=-1, resolution=(1632, 1232), fps=24, max_recording=15, iso=1600, shutter=2000, awb_mode='auto', awb_gains=(1.5, 1.5)):
    """Triggers remote capture and processing on connected hosts."""

    progress = gui[0]
    timer = gui[1]
    killer = False
    def statusCounter(status):
        while True:
            time.sleep(1)
            status.addSecond()
            nonlocal killer
            if killer:
                break

    # Allow for Single Remote Capture
    if ip != -1:
        ips = [IP[ip]]
        hosts = [HOST[ip]]
    else:
        ips = IP
        hosts = HOST

    # Establish Connections
    CAMERAS = []
    for client in ips:
        connection = remoteCamera(client, still)
        connection.hold("Session ID")
        connection.send(sessionID)
        connection.hold("Resolution")
        connection.send(resolution[0])
        connection.send(resolution[1])
        connection.hold("Frame Rate")
        connection.send(fps)
        connection.hold("Max Recording")
        connection.send(max_recording)
        connection.hold("ISO")
        connection.send(iso)
        connection.hold("Shutter Speed")
        connection.send(shutter)
        connection.hold("AWB Mode")
        connection.send(awb_mode)
        connection.hold("AWB Gains")
        connection.send(awb_gains[0])
        connection.send(awb_gains[1])
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

    # Start Recording Timer
    timeThread = threading.Thread(target=statusCounter, args=(timer,))
    timeThread.start()

    # Get Telemetry
    for i, camera in enumerate(CAMERAS):
        print("Recorded {} Frames on {}".format(camera.get(), hosts[i]))

    # End Recording Timer / Start Processing Timer
    killer = True
    timeThread.join()
    killer = False
    progress.advance()
    timer.reset()
    timeThread = threading.Thread(target=statusCounter, args=(timer,))
    timeThread.start()

    # Get Processing Telemetry
    for i, camera in enumerate(CAMERAS):
        print("Allocated Shared Memory in {} seconds on {}".format(camera.get(), hosts[i]))
    for i, camera in enumerate(CAMERAS):
        print("Multi Core Processing Completed in {} seconds on {}".format(camera.get(), hosts[i]))

    # Retrieve Data
    os.mkdir(os.path.join(STORAGE, sessionID))
    workspace = os.path.join(STORAGE, sessionID)
    for camera in CAMERAS:
        dataPath = camera.get()
        dataFile = os.path.basename(dataPath)
        dataLocal = os.path.join(workspace, dataFile)
        camera.getFile(dataPath, dataLocal)
        print("Recieved {}".format(dataFile))
    
    # End Processing Timer
    killer = True
    timeThread.join()
    progress.advance()

    return workspace
