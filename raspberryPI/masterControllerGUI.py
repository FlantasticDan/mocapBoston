import tkinter as tk
import RPi.GPIO as GPIO

class buttonInput:
    def __init__(self, GUI):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        edge = GPIO.FALLING
        GPIO.add_event_detect(17, edge, GUI.button1, 250)
        GPIO.add_event_detect(22, edge, GUI.button2, 250)
        GPIO.add_event_detect(23, edge, GUI.button3, 250)
        GPIO.add_event_detect(27, edge, GUI.button4, 250)

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

        header = tk.Label(self.grid, text=self.property, font=("Helvetica", 12))
        self.grid.grid_rowconfigure(0, minsize=30)
        header.grid(row=0, column=0, columnspan=len(self.options))

        self.labels = []
        self.grid.grid_rowconfigure(1, minsize=75)
        for i, display in enumerate(self.display):
            newOption = tk.Label(self.grid, text=display, font=("Helvetica", 20), fg="black")
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

        self.shutter = cameraSetting("Shutter Speed", [0, 16000, 8000, 4000, 2000, 1000, 500, 250], ["auto", "60", "125", "250", "500", "1000", "2000", "4000"])
        self.iso = cameraSetting("ISO", [0, 100, 200, 400, 800], ["auto", "100", "200", "400", "800"])
        self.fps = cameraSetting("Recording Frame Rate", [24, 18, 15, 12, 6, 3], ["24", "18", "15", "12", "6", "3"])
        self.maxTime = cameraSetting("Record Duration", [30, 15, 10, 5, 1], ["30", "15", "10", "5", "1"])

        buttonInput(self)
    
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

    def button1(self, pin):
        if self.screen == "shutterISO":
            self.destroyShutterISO()
            self.drawMainMenu()
        elif self.screen == "FPStime":
            self.destroyFPStime()
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

        self.header = tk.Label(self.container, bg=color, text=title, font=("Helvetica", 30))
        self.header.pack(fill="both", expand=1)

        self.container.place(width=640, height=105, y=(60 + (row - 1) * 105))
    
    def destroy(self):
        self.container.destroy()

root = tk.Tk()
gui = serverGUI(root)

root.mainloop()
