from direct.gui.DirectGui import DirectFrame
import cwiid
from direct.task import Task
from direct.stdpy import thread
import time

class Wiimote(object):
    def __init__(self, showbase):
        self.showbase = showbase
        wiimoteThread = thread.start_new_thread(self.connectController, args=())
        showbase.taskMgr.add(self.calculateHpr, "CalculateHpr")

    # This connects and calibrates a Wiimote
    def connectController(self):
        connectWiiText = DirectFrame(frameColor=(100, 100, 100, 1),
                            frameSize=(-1, 1, -0.1, 0.1),
                            pos=(0, 0, 0),
                            text="Press 1+2 on your Wiimote now...",
                            text_scale=(0.1,0.1))
        unconnected = True
        while unconnected:
            try:
                connectWiiText['text'] = "Press 1+2 on your Wiimote now..."
                self.wiimote = cwiid.Wiimote()
                unconnected = False
            except RuntimeError:
                connectWiiText['text'] = "Couldn't connect Wiimote.\nIs Bluetooth enabled?"
                time.sleep(2)
        time.sleep(1)
        self.wiimote.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_ACC | cwiid.RPT_MOTIONPLUS | cwiid.RPT_IR
        self.wiimote.enable(cwiid.FLAG_MOTIONPLUS)
        self.wiimote.led = 1
        print("Wiimote connected")

        connectWiiText['text'] = "Place the Wiimote on a flat surface."

        print()
        print("Starting calibration")
        while True:
            time.sleep(0.01)
            self.gyrobias = [0,0,0]
            self.accbias = [0,0,0]
            if 'motionplus' not in self.wiimote.state:
                continue
            def inner():
                for i in range(100):
                    for j in range(0,3):
                        self.gyrobias[j] = (self.gyrobias[j]*i + self.wiimote.state['motionplus']['angle_rate'][j]) / (i+1)
                        self.accbias[j] = (self.accbias[j]*i + self.wiimote.state['acc'][j]) / (i+1)
                        if abs(self.gyrobias[j] - self.wiimote.state['motionplus']['angle_rate'][j]) >= 20.0:
#                            print("Retrying. Reason: gyro ", j, ". ", i, " iterations.")
                            return
                        if abs(self.accbias[j] - self.wiimote.state['acc'][j]) > 1:
#                            print("Retrying. Reason: accelerometer ", j, ". ", i, " iterations.")
                            return False
                    time.sleep(0.01)
                print("Successful calibration")
                return True
            if inner():
                break

        self.accbias[2] = (self.accbias[0] + self.accbias[1]) / 2 # It's difficult to subtract gravity, so let's just assume a bias
        self.accbias[0] += 0.005 # To avoid a potential division by zero
        print("Gyro biases: ", self.gyrobias)
        print("Accelerometer biases: ", self.accbias)
        connectWiiText.destroy()
        self.showbase.motionControllerConnected = True


    # This calculates the likely orientation of the motion controller
    def calculateHpr(self, task):
        if not self.showbase.motionControllerConnected:
            return Task.cont

        accel = (self.wiimote.state['acc'][0]-122, self.wiimote.state['acc'][1]-122.9, self.wiimote.state['acc'][2]-122.5)
        if 'motionplus' in self.wiimote.state:
            angle_rates = self.wiimote.state['motionplus']['angle_rate']
            gyro = (
                (angle_rates[0]-self.gyrobias[0])/(4.0+self.wiimote.state['motionplus']['low_speed'][0]*16),
                (angle_rates[1]-self.gyrobias[1])/(4.0+self.wiimote.state['motionplus']['low_speed'][1]*16),
                (angle_rates[2]-self.gyrobias[2])/(4.0+self.wiimote.state['motionplus']['low_speed'][2]*16),
            )
        else:
            gyro = (0,0,0)
        self.showbase.fuse.update_nomag(accel, gyro, time.time())
        deltag2 = self.showbase.deltat(time.time()) * gyro[2]
        self.showbase.heading += deltag2

        if 'ir_src' in self.wiimote.state:
            ir1 = self.wiimote.state['ir_src'][0]
            ir2 = self.wiimote.state['ir_src'][1]
            # Range: X 0-1023, Y 0-767
            if self.wiimote.state['ir_src'][0] and self.wiimote.state['ir_src'][1]:
                self.showbase.heading = 0
        return Task.cont
