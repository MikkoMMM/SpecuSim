from motioncontrols.fusion import Fusion, DeltaT
from motioncontrols.wiimote import Wiimote
from math import pi, sin, cos, radians

from direct.gui.DirectGui import DirectFrame
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import Vec3, Vec4, ShaderTerrainMesh, Shader, load_prc_file_data
from panda3d.core import SamplerState, TextNode, TextureStage, TP_normal
from panda3d.core import CardMaker, Texture
from panda3d.core import PNMImage, Filename
from direct.task import Task
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import ZUp


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

        # Initialize the showbase
        ShowBase.__init__(self)

        # Increase camera FOV as well as the far plane
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)

        # The motion controller's orientation is to be updated 100 times this number per second
        self.motionControllerAccuracy = 40

        # Physics setup
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        # This is used to store which keys are currently pressed.
        self.keyMap = {
            "cam-forward": 0,
            "cam-backward": 0,
            "cam-left": 0,
            "cam-right": 0,
            "cam-turnleft": 0,
            "cam-turnright": 0,
        }
        self.motionControllerConnected = False
        self.disableMouse()

        # Construct the terrain
        self.terrain_node = ShaderTerrainMesh()

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale.png'))
        heightfield = Texture("heightfield")
        heightfield.load(elevation_img)
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
#        self.terrain.set_scale(8192, 8192, 50)
#        self.terrain.set_pos(-4096, -4096, -10.0)
        self.terrain.set_scale(8192, 8192, 50)
        self.terrain.set_pos(-4096, -4096, -10.0)

        # Set a shader on the terrain. The ShaderTerrainMesh only works with
        # an applied shader. You can use the shaders used here in your own application
        terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
        self.terrain.set_shader(terrain_shader)
        self.terrain.set_shader_input("camera", self.camera)

        # Set some texture on the terrain
        terrain_tex = self.loader.loadTexture("worldmaps/seed_16783_satellite.png")
        terrain_tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
        terrain_tex.set_anisotropic_degree(16)
        self.terrain.set_texture(terrain_tex)

        # Collision detection for the terrain
        terrainBulletNode = BulletRigidBodyNode("terrainBodyNode")
        terrain_colshape = BulletHeightfieldShape(elevation_img, 1.0, ZUp)
        terrainBulletNode.addShape(terrain_colshape)
        np = render.attachNewNode(terrainBulletNode)
        self.world.attachRigidBody(terrainBulletNode)
#        self.terrain.reparentTo(np)
        np.setScale(Vec3(8192, 8192, 50))
        np.setPos(-4096, -4096, 10)

        # Player character's shape and collision boxes
        shape = BulletBoxShape(Vec3(0.5, 0.5, 0.5))
        node = BulletRigidBodyNode('Box')
        node.setMass(1.0)
        node.addShape(shape)
        np = render.attachNewNode(node)
        np.setPos(0, 0, 2)
        self.world.attachRigidBody(node)
        self.player = loader.loadModel("models/unit_cube.bam")
        self.player.flattenLight()
        self.player.reparentTo(np)
        self.player.setScale(1)
        self.player.setPos(0, 2, 5)

        self.camera.setPos(0, 0, 5)

        # For calculating motion controller orientation
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        self.deltat = DeltaT(timediff)
        self.fuse = Fusion(2, timediff)

        self.inst1 = addInstructions(0.06, "[WASD]: Translate Camera")
        self.inst2 = addInstructions(0.12, "[QE]: Rotate Camera")

        self.accept("w", self.setKey, ["cam-forward", True])
        self.accept("s", self.setKey, ["cam-backward", True])
        self.accept("w-up", self.setKey, ["cam-forward", False])
        self.accept("s-up", self.setKey, ["cam-backward", False])
        self.accept("a", self.setKey, ["cam-left", True])
        self.accept("d", self.setKey, ["cam-right", True])
        self.accept("a-up", self.setKey, ["cam-left", False])
        self.accept("d-up", self.setKey, ["cam-right", False])
        self.accept("q", self.setKey, ["cam-turnleft", True])
        self.accept("e", self.setKey, ["cam-turnright", True])
        self.accept("q-up", self.setKey, ["cam-turnleft", False])
        self.accept("e-up", self.setKey, ["cam-turnright", False])

        # Connect, calibrate and start reading information from a motion controller
        self.motionController = Wiimote(self)

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.move, "moveTask")
        taskMgr.add(self.spinCameraTask, "SpinCameraTask")
        taskMgr.add(self.update, 'update')


    def update(self, task):
        dt = globalClock.getDt()
        # Choosing smaller substeps will make the simulation more realistic,
        # but performance will decrease too. Smaller substeps also reduce jitter.
        self.world.doPhysics(dt, 30, 1.0/540.0)
        return task.cont

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
        if self.keyMap["cam-turnleft"]:
            self.camera.setH(self.camera, +80 * dt)
        if self.keyMap["cam-turnright"]:
            self.camera.setH(self.camera, -80 * dt)

        return task.cont

    # Define a procedure to rotate the camera with a motion controller.
    def spinCameraTask(self, task):
        if not self.motionControllerConnected:
            return Task.cont

        self.camera.setHpr(self.heading, self.pitch, self.roll)
        return Task.cont

app = MyApp()
app.run()
