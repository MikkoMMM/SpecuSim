from motioncontrols.fusion import Fusion, DeltaT
import cwiid
import time
from math import pi, sin, cos, radians

from direct.gui.DirectGui import DirectFrame
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import Vec3, ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState, TextNode, TextureStage, TP_normal
from direct.task import Task
from direct.stdpy import thread

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
            stm-max-views 8

            # Further optimize the performance by reducing this to the max
            # number of chunks that will be visible at any given time.
            stm-max-chunk-count 2048

        """)

        self.render_pipeline = RenderPipeline()
        self.render_pipeline.create(self)

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

        # Set a shader on the terrain. The ShaderTerrainMesh only works with
        # an applied shader. You can use the shaders used here in your own application
        terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", self.camera)

        # Shortcut to view the wireframe mesh
        self.accept("f3", self.toggleWireframe)

        # Set some texture on the terrain
        grass_tex = self.loader.loadTexture("textures/grass.png")
        grass_tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
        grass_tex.set_anisotropic_degree(16)
        self.terrain.set_texture(grass_tex)

        # Load a skybox - you can safely ignore this code
        skybox = self.loader.loadModel("models/skybox.bam")
        skybox.reparent_to(self.render)
        skybox.set_scale(20000)

        skybox_texture = self.loader.loadTexture("textures/skybox.jpg")
        skybox_texture.set_minfilter(SamplerState.FT_linear)
        skybox_texture.set_magfilter(SamplerState.FT_linear)
        skybox_texture.set_wrap_u(SamplerState.WM_repeat)
        skybox_texture.set_wrap_v(SamplerState.WM_mirror)
        skybox_texture.set_anisotropic_degree(16)
        skybox.set_texture(skybox_texture)

        skybox_shader = Shader.load(Shader.SL_GLSL, "shaders/skybox.vert.glsl", "shaders/skybox.frag.glsl")
        skybox.set_shader(skybox_shader)

        # For calculating motion controller orientation
        self.heading = 0
        self.deltat = DeltaT(timediff)
        self.fuse = Fusion(timediff)

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

        wiimoteThread = thread.start_new_thread(self.connectWiimote, args=())

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.move, "moveTask")
        taskMgr.add(self.calculateHpr, "CalculateHpr")
        taskMgr.add(self.spinCameraTask, "SpinCameraTask")


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

    # This:
    # - connects a motion controller
    def connectWiimote(self):
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
        self.motionControllerConnected = True


    # This calculates the likely orientation of the motion controller
    def calculateHpr(self, task):
        if not self.motionControllerConnected:
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

    # Define a procedure to rotate the camera with a motion controller.
    def spinCameraTask(self, task):
        if not self.motionControllerConnected:
            return Task.cont

        self.camera.setHpr(self.heading, -self.fuse.roll, self.fuse.pitch)
        return Task.cont

app = MyApp()
app.run()
