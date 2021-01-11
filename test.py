import cwiid
import time
import math
from math import pi, sin, cos
from direct.gui.DirectGui import DirectFrame

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.stdpy import thread

def thread_function():

    return wiimote

#    while True:
#        print(wiimote.state)
#        print("Pitch: " + str(math.atan(wiimote.state['acc'][2]/wiimote.state['acc'][1])))
#        print("Roll: " + str(math.atan(wiimote.state['acc'][2]/wiimote.state['acc'][0])))


class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        myFrame = DirectFrame(frameColor=(100, 100, 100, 1),
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

        base.graphicsEngine.renderFrame()
        base.graphicsEngine.renderFrame()
        base.graphicsEngine.syncFrame()
#        wiimote = thread.start_new_thread(thread_function, args=())
        wiimote = cwiid.Wiimote()
        time.sleep(1)
        wiimote.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_ACC | cwiid.RPT_MOTIONPLUS | cwiid.RPT_IR
        wiimote.enable(cwiid.FLAG_MOTIONPLUS)

        wiimote.led = 1

        # Add the spinCameraTask procedure to the task manager.
        self.taskMgr.add(self.spinCameraTask, "SpinCameraTask")

    # Define a procedure to move the camera.
    def spinCameraTask(self, task):
        angleDegrees = task.time * 6.0
        angleRadians = angleDegrees * (pi / 180.0)
        self.camera.setPos(20 * sin(angleRadians), -20 * cos(angleRadians), 3)
        self.camera.setHpr(angleDegrees, 0, 0)
        return Task.cont


app = MyApp()
app.run()
