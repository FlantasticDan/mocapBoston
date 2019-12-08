import tkinter as tk
import os
import sys
import time
import pickle
import threading
import concurrent.futures
import cameraTrigger
import cameraCalibration as cc
import mocapSolver as solver

STORAGE = r"F:\mocapMath\Sandbox\rpi"
HOSTS = ["blueTriangle", "greenTriangle", "redY"]

class buttonInput:
    def __init__(self, GUI):
        self.GUI = GUI
    
    def rPiBinding(self):
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        edge = GPIO.FALLING
        GPIO.add_event_detect(17, edge, self.GUI.button1, 250)
        GPIO.add_event_detect(22, edge, self.GUI.button2, 250)
        GPIO.add_event_detect(23, edge, self.GUI.button3, 250)
        GPIO.add_event_detect(27, edge, self.GUI.button4, 250)
    
    def kbBinding(self):
        self.GUI.master.bind('1', self.GUI.button1)
        self.GUI.master.bind('2', self.GUI.button2)
        self.GUI.master.bind('3', self.GUI.button3)
        self.GUI.master.bind('4', self.GUI.button4)

class cameraSetting:
    def __init__(self, setting, options, display):
        self.property = setting
        self.options = options
        self.display = display
        self.index = 0
    
    def advance(self):
        """Changes the active selection."""
        self.labels[self.index]['fg'] = 'black'

        self.index += 1
        if self.index >= len(self.options):
            self.index = 0
        
        self.labels[self.index]['fg'] = 'red'
    
    def get(self):
        """Returns the activly selected option."""
        return self.options[self.index]
    
    def drawUI(self, master, row):
        """Creates the GUI for the camera setting in the specified row."""
        self.container = tk.Frame(master)
        self.grid = tk.Frame(self.container)

        header = tk.Label(self.grid, text=self.property, font=("Helvetica", 16))
        self.grid.grid_rowconfigure(0, minsize=30)
        header.grid(row=0, column=0, columnspan=len(self.options))

        self.labels = []
        self.grid.grid_rowconfigure(1, minsize=75)
        for i, display in enumerate(self.display):
            newOption = tk.Label(self.grid, text=display, font=("Helvetica", 30), fg="black")
            newOption.grid(row=1, column=i)
            self.grid.grid_columnconfigure(i, minsize=640/len(self.options))
            self.labels.append(newOption)
        
        self.labels[self.index]['fg'] = 'red'
        
        self.grid.pack(fill="both", expand=1)
        self.container.place(width=640, height=105, y=(60 + (row - 1) * 105))
    
    def destroy(self):
        self.container.destroy()

class camera:
    def __init__(self, cameraName):
        self.cameraPath = os.path.join(STORAGE, cameraName)
        self.cameraName = cameraName

        if os.path.isfile(os.path.join(self.cameraPath, "lens.npz")):
            self.matrix, self.distortion, self.fov = cc.importCalibration(os.path.join(self.cameraPath, "lens.npz"))
            self.lens = True
        else:
            self.lens = False

        if os.path.isfile(os.path.join(self.cameraPath, "world.camera")):
            with open(os.path.join(self.cameraPath, "world.camera"), "rb") as data:
                self.position, self.rotation = pickle.load(data)
            self.world = True
        else:
            self.world = False

    def isReady(self):
        if self.world and self.lens:
            return True
        else:
            return False
    
    def moveLensFile(self):
        os.rename(os.path.join(self.cameraPath, "lens.npz"), os.path.join(self.cameraPath, "lens", "lens-{}.npz".format(cameraTrigger.generateSession())))

    def moveWorldFile(self):
        os.rename(os.path.join(self.cameraPath, "world.camera"), os.path.join(self.cameraPath, "world", "world-{}.camera".format(cameraTrigger.generateSession())))
    
    def writeNewLensFile(self, matrix, distortion, fov):
        if self.lens:
            self.moveLensFile()

        self.matrix = matrix
        self.distortion = distortion
        self.fov = fov

        cc.exportCalibration(os.path.join(self.cameraPath, "lens"), matrix, distortion, fov)
        self.lens = True
    
    def writeNewWorldFile(self, position, rotation):
        if self.world:
            self.moveWorldFile()
        
        self.position = position
        self.rotation = rotation

        with open(os.path.join(self.cameraPath, "world.camera"), "wb") as data:
            payload = (position, rotation)
            pickle.dump(payload, data)
        
        self.world = True
        print("\n{} World Calibration:".format(self.cameraName))
        print("Position: {}".format(position))
        print("Rotation: {}\n".format(rotation))
    
    def getProperties(self):
        return (self.position[0], self.position[1], self.position[2], self.rotation[0], self.rotation[1], self.rotation[2], self.fov[0], self.fov[1])

class serverGUI:
    def __init__(self, master):
        self.master = master
        master.title("mocapBoston")
        master.minsize(width=640, height=480)
        master.maxsize(width=640, height=480)

        self.title = titleBar(master, "mocapBoston")
        self.drawMainMenu()

        # Configure Camera Capture Settings
        self.shutter = cameraSetting("Shutter Speed", [0, 16000, 8000, 4000, 2000, 1000, 500, 250], ["auto", "60", "125", "250", "500", "1K", "2K", "4K"])
        self.iso = cameraSetting("ISO", [0, 100, 200, 400, 800], ["auto", "100", "200", "400", "800"])
        self.fps = cameraSetting("Recording Frame Rate", [24, 18, 15, 12, 6, 3], ["24", "18", "15", "12", "6", "3"])
        self.awbMode = cameraSetting("AWB Mode", ["auto", "tungsten", "fluorescent", "sunlight"], ["auto", "tungsten", "f-scent", "sun"])
        self.maxTime = cameraSetting("Record Duration", [30, 15, 10, 5, 1], ["30", "15", "10", "5", "1"])
        self.pattern = cameraSetting("Calibration Pattern", ["6-4-", "9-7-"], ["6x4", "9x7"])
        self.cameraSelect = cameraSetting("Camera Selection", [0, 1, 2, 3], ["blueTri", "greenTri", "redY", "cyanY"])

        # Setup Inputs, Configured to Allow non-RPi Debugging via Keyboard
        self.interface = buttonInput(self)
        try:
            self.interface.rPiBinding()
        except ModuleNotFoundError:
            print("RPI GPIO Inputs weren't detected.")
        finally:
            self.interface.kbBinding()
        
        # Configure Camera Calibrations
        self.cameras = []
        for client in HOSTS:
            self.cameras.append(camera(client))
        
        # Attach World Calibration Pattern
        self.worldPattern = cc.importMarkerPlacement(os.path.join(STORAGE, "worldPattern.txt"))
    
    def drawMainMenu(self):
        self.recording = buttonTitleBar(self.master, "Recording", "#FF6259", 1)
        self.lens = buttonTitleBar(self.master, "Lens Calibration", "#FF62E0", 2)
        self.worldOrient = buttonTitleBar(self.master, "World Orientation", "#86FF78", 3)
        self.settings = buttonTitleBar(self.master, "Camera Settings", "#80BEBF", 4)
        self.screen = "main"
    
    def destroyMainMenu(self):
        self.recording.destroy()
        self.lens.destroy()
        self.worldOrient.destroy()
        self.settings.destroy()

    def drawShutterISO(self):
        self.back = buttonTitleBar(self.master, "Return to the Menu", "grey", 1)
        self.shutter.drawUI(self.master, 2)
        self.iso.drawUI(self.master, 3)
        self.next = buttonTitleBar(self.master, "More Settings", "grey", 4)
        self.screen = "shutterISO"
    
    def destroyShutterISO(self):
        self.back.destroy()
        self.shutter.destroy()
        self.iso.destroy()
        self.next.destroy()
    
    def drawFPStime(self):
        self.back = buttonTitleBar(self.master, "Return to the Menu", "grey", 1)
        self.fps.drawUI(self.master, 2)
        self.maxTime.drawUI(self.master, 3)
        self.next = buttonTitleBar(self.master, "More Settings", "grey", 4)
        self.screen = "FPStime"
    
    def destroyFPStime(self):
        self.back.destroy()
        self.fps.destroy()
        self.maxTime.destroy()
        self.next.destroy()
    
    def drawAWBshutdown(self):
        self.back = buttonTitleBar(self.master, "Return to the Menu", "grey", 1)
        self.awbMode.drawUI(self.master, 2)
        self.shutdown = buttonTitleBar(self.master, "Shutdown Clients", "#FF62E0", 3)
        self.exit = buttonTitleBar(self.master, "Exit", "#FF6259", 4)
        self.screen = "AWBshutdown"
    
    def destroyAWBshutdown(self):
        self.back.destroy()
        self.awbMode.destroy()
        self.shutdown.destroy()
        self.exit.destroy()

    def drawRecording(self):
        self.back = buttonTitleBar(self.master, "Return to the Menu", "grey", 1)
        self.start = buttonTitleBar(self.master, "Start Capture", "#FF6259", 4)
        self.screen = "Recording"
    
    def destroyRecording(self):
        self.back.destroy()
        self.start.destroy()
    
    def startCapture(self):
        # Draw UI
        self.sessionID = cameraTrigger.generateSession()
        self.session = cameraSetting("Session ID", [self.sessionID], [self.sessionID])
        self.session.drawUI(self.master, 1)
        self.status = cameraSetting("Status", ["Recording", "Processing", "Solving"], ["Recording", "Processing", "Solving"])
        self.status.drawUI(self.master, 2)
        self.timer = statusTimer(self.master, "Time Elapsed", 3)
        self.screen = "Capture"

        # Start Capture Process
        self.captureExecutor = concurrent.futures.ThreadPoolExecutor()
        self.captureFuture = self.captureExecutor.submit(cameraTrigger.remoteCapture, self.sessionID, (self.status, self.timer),
                                                        still=False, ip=-1, resolution=(1632, 1232), fps=self.fps.get(),
                                                        max_recording=self.maxTime.get(), iso=self.iso.get(), shutter=self.shutter.get(),
                                                        awb_mode=self.awbMode.get())
        self.captureFuture.add_done_callback(self.finishedCapture)
    
    def finishedCapture(self, future):
        self.captureDirectory = future.result()
        self.timer.reset()

        # Redraw UI
        self.timer.reset()
        killer = False
        def statusCounter(status):
            while True:
                time.sleep(1)
                status.addSecond()
                nonlocal killer
                if killer:
                    break
        # Start Recording Timer
        timeThread = threading.Thread(target=statusCounter, args=(self.timer,))
        timeThread.start()

        markers = []
        cameras = []
        length = 10000
        for mocap in os.listdir(self.captureDirectory):
            cameraID = mocap.split("_")[0]
            cameraIndex = HOSTS.index(cameraID)
            cam = self.cameras[cameraIndex]
            cameras.append(cam)

            mocapFile = os.path.join(self.captureDirectory, mocap)
            with open(mocapFile, "rb") as binary:
                marker = pickle.load(binary)
            
            markers.append(marker)
            if len(marker) < length:
                length = len(marker)
            
        frame = 0
        self.solved = []
        while frame < length:
            persp = []
            for i, angle in enumerate(markers):
                camProps = cameras[i].getProperties()
                persp.append((angle[frame], camProps))        
            self.solved.append(solver.solveFrame(*persp))
            frame += 1
        
        # Post Processing
        with open(os.path.join(self.captureDirectory, "solve.mocap"), "wb") as data:
            pickle.dump(self.solved, data)

        # UI Cleanup
        killer = True
        timeThread.join()
        self.status.destroy()
        self.timer.destroy()
        self.start = buttonTitleBar(self.master, "New Capture", "#FF6259", 4)
        self.screen = "finishedCapture"

    def lensCapture(self):
        self.back = buttonTitleBar(self.master, "Return to the Menu", "grey", 1)
        self.cameraSelect.drawUI(self.master, 2)
        self.pattern.drawUI(self.master, 3)
        self.start = buttonTitleBar(self.master, "Start Lens Calibration", "#FF62E0", 4)
        self.screen = "LensCapture"
    
    def destroyLensCapture(self):
        self.back.destroy()
        self.cameraSelect.destroy()
        self.pattern.destroy()
        self.start.destroy()

    def runLensCapture(self):
        # Draw UI
        self.sessionID = self.pattern.get() + cameraTrigger.generateSession()
        self.session = cameraSetting("Session ID", [self.sessionID], [self.sessionID])
        self.session.drawUI(self.master, 1)
        self.status = cameraSetting("Status", ["Recording", "Processing"], ["Recording", "Processing"])
        self.status.drawUI(self.master, 2)
        self.timer = statusTimer(self.master, "Time Elapsed", 3)
        self.screen = "runLensCapture"

        # Start Lens Capture Process
        self.lensCaptureExecutor = concurrent.futures.ThreadPoolExecutor()
        self.lensCaptureFuture = self.lensCaptureExecutor.submit(cameraTrigger.remoteCapture, self.sessionID, (self.status, self.timer),
                                                        still=False, ip=self.cameraSelect.get(), resolution=(1632, 1232), fps=self.fps.get(),
                                                        max_recording=self.maxTime.get(), iso=self.iso.get(), shutter=self.shutter.get(),
                                                        awb_mode=self.awbMode.get())
        self.lensCaptureFuture.add_done_callback(self.finishedLensCapture)
    
    def finishedLensCapture(self, future):
        lensCaptureDirectory = future.result()

        # Redraw Relevant UI
        self.status.destroy()
        self.timer.destroy()
        
        # Save Lens Calibration into Camera Class
        for calibration in os.listdir(lensCaptureDirectory):
            path = os.path.join(lensCaptureDirectory, calibration)
            matrix, distortion, fov = cc.importCalibration(path)
            self.cameras[self.cameraSelect.get()].writeNewLensFile(matrix, distortion, fov)
            break
        
        self.restart = buttonTitleBar(self.master, "New Lens Calibration", "#FF62E0", 4)
        self.screen = "endLensCapture"

    def worldOrientation(self):
        self.back = buttonTitleBar(self.master, "Return to the Menu", "grey", 1)
        self.start = buttonTitleBar(self.master, "Start World Orientation", "#86FF78", 4)
        self.screen = "worldOrient"
    
    def destoryWorldOrientation(self):
        self.back.destroy()
        self.start.destroy()

    def runWorldOrientation(self):
        self.sessionID = cameraTrigger.generateSession()
        self.session = cameraSetting("Session ID", [self.sessionID], [self.sessionID])
        self.session.drawUI(self.master, 1)
        self.status = cameraSetting("Status", ["Recording", "Processing", "Solving"], ["Recording", "Processing", "Solving"])
        self.status.drawUI(self.master, 2)
        self.timer = statusTimer(self.master, "Time Elapsed", 3)
        self.screen = "runWorldOrient"

        self.worldOrientExecutor = concurrent.futures.ThreadPoolExecutor()
        self.worldOrientFuture = self.worldOrientExecutor.submit(cameraTrigger.remoteCapture, self.sessionID, (self.status, self.timer),
                                                        still=False, ip=-1, resolution=(1632, 1232), fps=10,
                                                        max_recording=5, iso=self.iso.get(), shutter=self.shutter.get(),
                                                        awb_mode=self.awbMode.get())
        self.worldOrientFuture.add_done_callback(self.finishedWorldOrient)
    
    def finishedWorldOrient(self, future):
        self.worldMarkersDir = future.result()

        # Redraw UI
        self.timer.reset()
        killer = False
        def statusCounter(status):
            while True:
                time.sleep(1)
                status.addSecond()
                nonlocal killer
                if killer:
                    break
        # Start Recording Timer
        timeThread = threading.Thread(target=statusCounter, args=(self.timer,))
        timeThread.start()

        for mocap in os.listdir(self.worldMarkersDir):
            cameraID = mocap.split("_")[0]
            cameraIndex = HOSTS.index(cameraID)
            cam = self.cameras[cameraIndex]

            mocapFile = os.path.join(self.worldMarkersDir, mocap)
            with open(mocapFile, "rb") as binary:
                markers = pickle.load(binary)
            
            imagePoints, objectPoints = cc.correlatePlacementWithDetection(self.worldPattern, markers[25])
            position, rotation = cc.solveCamera(cam.matrix, cam.distortion, imagePoints, objectPoints)

            cam.writeNewWorldFile(position, rotation)
        
        killer = True
        timeThread.join()
        self.timer.destroy()
        self.status.destroy()
        self.back = buttonTitleBar(self.master, "Back to Menu", "#86FF78", 4)
        self.screen = "endWorldOrient"
    
    def destroyEndWorldOrient(self):
        self.back.destroy()
        self.session.destroy()

    def button1(self, pin):
        if self.screen == "shutterISO":
            self.destroyShutterISO()
            self.drawMainMenu()
        elif self.screen == "FPStime":
            self.destroyFPStime()
            self.drawMainMenu()
        elif self.screen == "main":
            self.destroyMainMenu()
            self.drawRecording()
        elif self.screen == "Recording":
            self.destroyRecording()
            self.drawMainMenu()
        elif self.screen == "LensCapture":
            self.destroyLensCapture()
            self.drawMainMenu()
        elif self.screen == "AWBshutdown":
            self.destroyAWBshutdown()
            self.drawMainMenu()
        elif self.screen == "worldOrient":
            self.destoryWorldOrientation()
            self.drawMainMenu()

    
    def button2(self, pin):
        if self.screen == "shutterISO":
            self.shutter.advance()
        elif self.screen == "FPStime":
            self.fps.advance()
        elif self.screen == "main":
            self.destroyMainMenu()
            self.lensCapture()
        elif self.screen == "LensCapture":
            self.cameraSelect.advance()
        elif self.screen == "AWBshutdown":
            self.awbMode.advance()

    def button3(self, pin):
        if self.screen == "shutterISO":
            self.iso.advance()
        elif self.screen == "FPStime":
            self.maxTime.advance()
        elif self.screen == "LensCapture":
            self.pattern.advance()
        elif self.screen == "AWBshutdown":
            cameraTrigger.shutdown()
        elif self.screen == "main":
            self.destroyMainMenu()
            self.worldOrientation()

    def button4(self, pin):
        if self.screen == "main":
            self.destroyMainMenu()
            self.drawShutterISO()
        elif self.screen == "shutterISO":
            self.destroyShutterISO()
            self.drawFPStime()
        elif self.screen == "FPStime":
            self.destroyFPStime()
            self.drawAWBshutdown()
        elif self.screen == "AWBshutdown":
            sys.exit()
        elif self.screen == "Recording":
            self.destroyRecording()
            self.startCapture()
        elif self.screen == "LensCapture":
            self.destroyLensCapture()
            self.runLensCapture()
        elif self.screen == "endLensCapture":
            self.lensCaptureExecutor.shutdown()
            self.session.destroy()
            self.restart.destroy()
            self.lensCapture()
        elif self.screen == "endWorldOrient":
            self.worldOrientExecutor.shutdown()
            self.destroyEndWorldOrient()
            self.drawMainMenu()
        elif self.screen == "worldOrient":
            self.destoryWorldOrientation()
            self.runWorldOrientation()
        elif self.screen == "finishedCapture":
            self.captureExecutor.shutdown()
            self.session.destroy()
            self.start.destroy()
            self.drawRecording()

class titleBar:
    def __init__(self, master, title):
        self.container = tk.Frame(master)
        self.title = title

        self.header = tk.Label(self.container, bg="black", text=self.title, font=("Helvetica", 16), fg="white")
        self.header.pack(fill="both", expand=1)

        self.container.place(width=640, height=60)

class buttonTitleBar:
    def __init__(self, master, title, color, row):
        self.container = tk.Frame(master)
        self.text = title

        self.header = tk.Label(self.container, bg=color, text=self.text, font=("Helvetica", 30))
        self.header.pack(fill="both", expand=1)

        self.container.place(width=640, height=105, y=(60 + (row - 1) * 105))
    
    def destroy(self):
        self.container.destroy()

class statusTimer:
    def __init__(self, master, title, row):
        self.container = tk.Frame(master)
        self.grid = tk.Frame(self.container)

        # Small Header
        header = tk.Label(self.grid, text=title, font=("Helvetica", 16))
        self.grid.grid_rowconfigure(0, minsize=30)
        self.grid.grid_columnconfigure(0, minsize=640)
        header.grid(row=0, column=0)

        # Timer Variables
        self.display = tk.StringVar()
        self.display.set("Not Started")
        self.elapsed = 0

        # Timer Display
        self.grid.grid_rowconfigure(1, minsize=75)
        self.timer = tk.Label(self.grid, textvariable=self.display, font=("Helvetica", 30), fg="black")
        self.timer.grid(row=1, column=0)

        # Place Widgets
        self.grid.pack(fill="both", expand=1)
        self.container.place(width=640, height=105, y=(60 + (row - 1) * 105))
    
    def destroy(self):
        self.container.destroy()
    
    def addSecond(self):
        self.elapsed += 1
        seconds = self.elapsed % 60
        minutes = self.elapsed // 60

        if minutes < 1:
            self.display.set("{}".format(seconds))
            return None

        self.display.set("{}:{:02d}".format(minutes, seconds))

    def reset(self):
        self.elapsed = -1

root = tk.Tk()
gui = serverGUI(root)
try:
    root.attributes('-fullscreen', True)
except tk.TclError:
    print("Couldn't Enter Fullscreen")

root.mainloop()
