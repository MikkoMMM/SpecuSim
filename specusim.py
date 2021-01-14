from motioncontrols.fusion import Fusion, DeltaT
from motioncontrols.wiimote import Wiimote
from math import pi, sin, cos, radians

from direct.gui.DirectGui import DirectFrame
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import Vec3, ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState, TextNode, TextureStage, TP_normal
from direct.task import Task

from rpcore import RenderPipeline


def timediff(time1, time2):
    return (time1-time2)


# Function to put instructions on the screen.
def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                        shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                        pos=(0.08, -pos - 0.04), align=TextNode.ALeft)


class MyApp(ShowBase):
    def __init__(self):
        # Load some configuration variables, its important for this to happen
        # before the ShowBase is initialized
        load_prc_file_data("", """
            textures-power-2 none
            gl-coordinate-system default
            window-title SpecuSim - An Early Prototype

            # As an optimization, set this to the maximum number of cameras
            # or lights that will be rendering the terrain at any given time.
            stm-max-views 20

            # Further optimize the performance by reducing this to the max
            # number of chunks that will be visible at any given time.
            stm-max-chunk-count 2048

        """)

        self.render_pipeline = RenderPipeline()
        self.render_pipeline.create(self)

        # The motion controller's orientation is to be updated 100 times this number per second
        self.motionControllerAccuracy = 40

        # Set time of day
        self.render_pipeline.daytime_mgr.time = "16:25"

        # This is used to store which keys are currently pressed.
        self.keyMap = {
            "cam-forward": 0,
            "cam-backward": 0,
            "cam-left": 0,
            "cam-right": 0,
        }
        self.motionControllerConnected = False
        self.disableMouse()

        # Increase camera FOV as well as the far plane
#        self.camLens.set_fov(90)
#        self.camLens.set_near_far(0.1, 50000)

        # Construct the terrain
        self.terrain_node = ShaderTerrainMesh()

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        heightfield = self.loader.loadTexture("worldmaps/seed_16783_grayscale.png")
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp
        self.terrain_node.heightfield = heightfield

        # Set the target triangle width. For a value of 10.0 for example,
        # the terrain will attempt to make every triangle 10 pixels wide on screen.
        self.terrain_node.target_triangle_width = 10.0

        # Generate the terrain
        self.terrain_node.generate()

        # Attach the terrain to the main scene and set its scale. With no scale
        # set, the terrain ranges from (0, 0, 0) to (1, 1, 1)
        self.terrain = self.render.attach_new_node(self.terrain_node)
        self.terrain.set_scale(8192, 8192, 50)
        self.terrain.set_pos(-4096, -4096, -10.0)

        # For calculating motion controller orientation
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        self.deltat = DeltaT(timediff)
        self.fuse = Fusion(1.5, timediff)

        self.inst1 = addInstructions(0.06, "[W]: Move Camera Forward")
        self.inst2 = addInstructions(0.12, "[A]: Move Camera Left")
        self.inst3 = addInstructions(0.18, "[S]: Move Camera Right")
        self.inst4 = addInstructions(0.24, "[D]: Move Camera Backward")

        self.accept("w", self.setKey, ["cam-forward", True])
        self.accept("s", self.setKey, ["cam-backward", True])
        self.accept("w-up", self.setKey, ["cam-forward", False])
        self.accept("s-up", self.setKey, ["cam-backward", False])
        self.accept("a", self.setKey, ["cam-left", True])
        self.accept("d", self.setKey, ["cam-right", True])
        self.accept("a-up", self.setKey, ["cam-left", False])
        self.accept("d-up", self.setKey, ["cam-right", False])

        # Connect, calibrate and start reading information from a motion controller
        self.motionController = Wiimote(self)

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.move, "moveTask")
        taskMgr.add(self.spinCameraTask, "SpinCameraTask")
        self.reload_shaders()


    # Records the state of the arrow keys
    def setKey(self, key, value):
        self.keyMap[key] = value

    # Moves the camera with key presses
    # Also deals with grid checking and collision detection
    def move(self, task):

        # Get the time that elapsed since last frame.  We multiply this with
        # the desired speed in order to find out with which distance to move
        # in order to achieve that desired speed.
        dt = globalClock.getDt()

        # If the camera-left key is pressed, move camera left.
        # If the camera-right key is pressed, move camera right.

        if self.keyMap["cam-forward"]:
            self.camera.setY(self.camera, +80 * dt)
        if self.keyMap["cam-backward"]:
            self.camera.setY(self.camera, -80 * dt)
        if self.keyMap["cam-left"]:
            self.camera.setX(self.camera, -80 * dt)
        if self.keyMap["cam-right"]:
            self.camera.setX(self.camera, +80 * dt)

        return task.cont

    def reload_shaders(self):
        self.render_pipeline.reload_shaders()

        # Set the terrain effect
        self.render_pipeline.set_effect(self.terrain, "effects/terrain-effect.yaml", {}, 100)

    # Define a procedure to rotate the camera with a motion controller.
    def spinCameraTask(self, task):
        if not self.motionControllerConnected:
            return Task.cont

        self.camera.setHpr(self.heading, self.pitch, self.roll)
        return Task.cont

app = MyApp()
app.run()
