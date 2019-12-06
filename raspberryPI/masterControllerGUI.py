import tkinter as tk
import time
import threading
import cameraTrigger
import concurrent.futures

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

class serverGUI:
    def __init__(self, master):
        self.master = master
        master.title("mocapBoston")
        master.minsize(width=640, height=480)
        master.maxsize(width=640, height=480)

        self.title = titleBar(master, "mocapBoston")
        self.drawMainMenu()

        self.shutter = cameraSetting("Shutter Speed", [0, 16000, 8000, 4000, 2000, 1000, 500, 250], ["auto", "60", "125", "250", "500", "1K", "2K", "4K"])
        self.iso = cameraSetting("ISO", [0, 100, 200, 400, 800], ["auto", "100", "200", "400", "800"])
        self.fps = cameraSetting("Recording Frame Rate", [24, 18, 15, 12, 6, 3], ["24", "18", "15", "12", "6", "3"])
        self.maxTime = cameraSetting("Record Duration", [30, 15, 10, 5, 1], ["30", "15", "10", "5", "1"])

        # Setup Inputs, Configured to Allow non-RPi Debugging via Keyboard
        self.interface = buttonInput(self)
        try:
            self.interface.rPiBinding()
        except ModuleNotFoundError:
            print("RPI GPIO Inputs weren't detected.")
        finally:
            self.interface.kbBinding()
    
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
                                                        awb_mode='auto', awb_gains=(1.5, 1.5))
        self.captureFuture.add_done_callback(self.finishedCapture)
    
    def finishedCapture(self, future):
        self.captureDirectory = future.result()
        self.timer.reset()


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
    
    def button2(self, pin):
        if self.screen == "shutterISO":
            self.shutter.advance()
        elif self.screen == "FPStime":
            self.fps.advance()

    def button3(self, pin):
        if self.screen == "shutterISO":
            self.iso.advance()
        elif self.screen == "FPStime":
            self.maxTime.advance()

    def button4(self, pin):
        if self.screen == "main":
            self.destroyMainMenu()
            self.drawShutterISO()
        elif self.screen == "shutterISO":
            self.destroyShutterISO()
            self.drawFPStime()
        elif self.screen == "FPStime":
            self.destroyFPStime()
            self.drawShutterISO()
        elif self.screen == "Recording":
            self.destroyRecording()
            self.startCapture()

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

root.mainloop()
