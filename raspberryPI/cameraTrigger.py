import paramiko
import time
import random

def generateSession():
    """Generates a Random 4 Digit Hex"""
    randomInt = random.randint(4096, 65535)
    hexInt = format(randomInt, 'X')
    return hexInt

def holdForString(output, checksum):
    check = output.readline()

    # Refuse Empty Lines
    while check == '\n':
        check = output.readline()

    check = check.rstrip()
    if check == checksum:
        return True
    else:
        raise Exception

def getTelemtry(output):
    payload = output.readline()
    
    # Refuse Empty Lines
    while payload == '\n':
        payload = output.readline()
    
    payload = payload.rstrip()
    payload = payload.split(" : ")
    return payload[1]


def sendString(inStream, payload):
    inStream.write("{}\n".format(payload))
    inStream.flush()

# Create Session Variables
sessionID = generateSession()

# Establish SSH Connection
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.113", username="pi", password="mocapMath")

i, o, e = ssh.exec_command("cd /home/pi/Documents; python3 cameraController.py")

holdForString(o, "Session ID")
sendString(i, sessionID)

holdForString(o, "Record Delay")
sendString(i, "1")

recordedFrames = getTelemtry(o)
print("Recorded {} Frames".format(recordedFrames))
sharedMemoryTime = getTelemtry(o)
print("Allocated Shared Memory in {} seconds".format(sharedMemoryTime))
processTime = getTelemtry(o)
print("Multi Core Processing Completed in {} seconds".format(processTime))

# Retrieve Data
filePath = getTelemtry(o)
print("Data Exported at {} on SSH Client".format(filePath))