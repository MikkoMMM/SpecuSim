from direct.gui.DirectGui import DirectFrame
import cwiid
from direct.task import Task
from direct.stdpy import thread
import time
import math

class Wiimote(object):
    def __init__(self, showbase):
        self.showbase = showbase
        wiimoteThread = thread.start_new_thread(self.connectController, args=())
        hprThread = thread.start_new_thread(self.calculateHpr, args=())

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
        flatSurfaceText = "Place the Wiimote on a flat surface."

        connectWiiText['text'] = flatSurfaceText

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
                            connectWiiText['text'] = flatSurfaceText
                            return
                        if abs(self.accbias[j] - self.wiimote.state['acc'][j]) > 1:
                            connectWiiText['text'] = flatSurfaceText
                            return False
                    time.sleep(0.01)
                if abs(self.accbias[1] - self.accbias[0]) > 1.5 or self.accbias[2] < self.accbias[1]:
                    connectWiiText['text'] = "The Wiimote must be face up."
                    return False
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
    def calculateHpr(self):
        heading = self.showbase.heading

        while True:
            time.sleep(1/(100*self.showbase.motionControllerAccuracy)) # Having less time between updates increases accuracy but is obviously also computationally expensive
            if not self.showbase.motionControllerConnected:
                time.sleep(0.005)
                continue

            accel = (self.wiimote.state['acc'][0]-self.accbias[0], self.wiimote.state['acc'][1]-self.accbias[1], self.wiimote.state['acc'][2]-self.accbias[2])
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
            heading += deltag2

            # Reset the heading if pointed at an IR source
            if 'ir_src' in self.wiimote.state:
                ir1 = self.wiimote.state['ir_src'][0]
                ir2 = self.wiimote.state['ir_src'][1]
                # Range: X 0-1023, Y 0-767
                if self.wiimote.state['ir_src'][0]:
                    try:
                        x = (self.wiimote.state['ir_src'][0]['pos'][0] + self.wiimote.state['ir_src'][1]['pos'][0]) / 2
                        if 0.45*1024 < x and x < 0.55*1024:
                            heading = 0
                    except:
                        pass # Due to asynchronous nature, a try-except was possibly necessary in any case

            self.showbase.pitch = -self.showbase.fuse.roll
            self.showbase.heading = heading
            self.showbase.roll = self.showbase.fuse.pitch
