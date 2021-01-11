from fusion import Fusion
import cwiid
import time
from deltat import DeltaT
from math import pi, sin, cos, radians
from direct.gui.DirectGui import DirectFrame

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

def timediff(time1, time2):
    return (time1-time2)

class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        connectWiiText = DirectFrame(frameColor=(100, 100, 100, 1),
                            frameSize=(-1, 1, -0.1, 0.1),
                            pos=(0, 0, 0),
                            text="Press 1+2 on your Wiimote now...",
                            text_scale=(0.1,0.1))


        # Load the environment model.
        self.scene = self.loader.loadModel("models/environment")
        # Reparent the model to render.
        self.scene.reparentTo(self.render)
        # Apply scale and position transforms on the model.
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)
        self.camera.setPos(0, -10, 3)

        # For calculating motion controller orientation
        self.heading = 0
        self.deltat = DeltaT(timediff)
        self.fuse = Fusion(timediff)

        # Render the very first frame
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.syncFrame()

        self.wiimote = cwiid.Wiimote()
        time.sleep(1)
        self.wiimote.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_ACC | cwiid.RPT_MOTIONPLUS | cwiid.RPT_IR
        self.wiimote.enable(cwiid.FLAG_MOTIONPLUS)
        self.wiimote.led = 1

        connectWiiText.destroy()

        # Tasks that are repeated ad infinitum
        self.taskMgr.add(self.calculateHpr, "CalculateHpr")
        self.taskMgr.add(self.spinCameraTask, "SpinCameraTask")

    def calculateHpr(self, task):
        accel = (self.wiimote.state['acc'][0]-122, self.wiimote.state['acc'][1]-122.9, self.wiimote.state['acc'][2]-122.5)
        if 'motionplus' in self.wiimote.state:
            angle_rates = self.wiimote.state['motionplus']['angle_rate']
            gyro = (
                (angle_rates[0]-7945)/(4.0+self.wiimote.state['motionplus']['low_speed'][0]*16),
                (angle_rates[1]-8115)/(4.0+self.wiimote.state['motionplus']['low_speed'][1]*16),
                (angle_rates[2]-7964)/(4.0+self.wiimote.state['motionplus']['low_speed'][2]*16),
            )
        else:
            gyro = (0,0,0)
        self.fuse.update_nomag(accel, gyro, time.time())
        deltag2 = self.deltat(time.time()) * gyro[2]
        self.heading += deltag2

        if 'ir_src' in self.wiimote.state:
            ir1 = self.wiimote.state['ir_src'][0]
            ir2 = self.wiimote.state['ir_src'][1]
            # Range: X 0-1023, Y 0-767
            if self.wiimote.state['ir_src'][0] and self.wiimote.state['ir_src'][1]:
                self.heading = 0
        return Task.cont

    # Define a procedure to move the camera.
    def spinCameraTask(self, task):
        self.camera.setPos(0, -10, 3)
        self.camera.setHpr(self.heading, -self.fuse.roll, self.fuse.pitch)
        return Task.cont


app = MyApp()
app.run()
