from motioncontrols.fusion import Fusion, DeltaT
from motioncontrols.wiimote import Wiimote
from math import pi, sin, cos, radians

from direct.showbase.InputStateGlobal import inputState
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
from panda3d.bullet import BulletDebugNode
from panda3d.core import BitMask32
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import ZUp
from direct.showbase import PythonUtil


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
        base.setFrameRateMeter(True)

        # Increase camera FOV as well as the far plane
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)
        
        #Heightfield's height
        self.height = 25.0

        # The motion controller's orientation is to be updated 100 times this number per second
        self.motionControllerAccuracy = 40

        # Physics setup
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))
        '''
        # These would show wireframes for the physics objects.
        # However, the normal heightfield is too large for this to work. Switch to a smaller one if you wish to visually debug.
        self.worldNP = render.attachNewNode('World')
        self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.show()
        self.debugNP.node().showNormals(True)
        self.world.setDebugNode(self.debugNP.node())
        '''
        self.motionControllerConnected = False
        self.disableMouse()

        # Construct the terrain
        self.terrain_node = ShaderTerrainMesh()

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale.png'))
        elevation_img_size = elevation_img.getXSize()
        elevation_img_offset = elevation_img_size / 2.0 - 0.5
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
        self.terrain = render.attach_new_node(self.terrain_node)
        self.terrain.set_scale(elevation_img_size, elevation_img_size, self.height)
        self.terrain.set_pos(-elevation_img_offset, -elevation_img_offset, -self.height/2)

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
        terrain_colshape = BulletHeightfieldShape(elevation_img, self.height, ZUp)
        terrain_colshape.setUseDiamondSubdivision(True)
        terrainBulletNode.addShape(terrain_colshape)
        np = render.attachNewNode(terrainBulletNode)
        np.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(terrainBulletNode)
        np.setScale(Vec3(1, 1, 1))
        np.setPos(0, 0, 0)

        # Player character's shape and collision boxes
        shape = BulletBoxShape(Vec3(0.5, 0.5, 0.5))
        self.player = self.render.attachNewNode(BulletRigidBodyNode('Box'))
        self.player.node().setMass(80.0)
        self.player.node().addShape(shape)
        self.player.node().setAngularFactor(Vec3(0,0,0.1))
        self.player.node().setAngularDamping(0.9)
        self.player.node().setFriction(0.8)
        terrainBulletNode.setFriction(0.8)
        self.player.node().setRestitution(0.0)
        terrainBulletNode.setRestitution(0.1)
        self.player.setPos(0, 0, 1)
        self.player.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(self.player.node())
        playerVisual = loader.loadModel("models/unit_cube.bam")
#        playerVisual.flattenLight()
        playerVisual.clearModelNodes()
        playerVisual.reparentTo(self.player)

        self.camera.reparentTo(self.player)
        self.camera.setPos(0, -10, 40)
        self.camera.lookAt(self.player, 0, 5, 0)

        # For calculating motion controller orientation
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        self.deltat = DeltaT(timediff)
        self.fuse = Fusion(2, timediff)

        self.inst1 = addInstructions(0.06, "[WASD]: Translate Camera")
        self.inst2 = addInstructions(0.12, "[QE]: Rotate Camera")
        self.inst3 = addInstructions(0.18, "")
        self.inst4 = addInstructions(0.24, "")
        self.inst5 = addInstructions(0.30, "")

        self.accept('f1', self.toggleWireframe)
        self.accept('f2', self.toggleTexture)
        inputState.watchWithModifiers('cam-forward', 'w')
        inputState.watchWithModifiers('cam-left', 'a')
        inputState.watchWithModifiers('cam-backward', 's')
        inputState.watchWithModifiers('cam-right', 'd')
        inputState.watchWithModifiers('cam-turnleft', 'q')
        inputState.watchWithModifiers('cam-turnright', 'e')

        # Connect, calibrate and start reading information from a motion controller
#        self.motionController = Wiimote(self)

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

    # Moves the camera with key presses
    # Also deals with grid checking and collision detection
    def move(self, task):

        # Get the time that elapsed since last frame.  We multiply this with
        # the desired speed in order to find out with which distance to move
        # in order to achieve that desired speed.
        dt = globalClock.getDt()
        
        force = Vec3(0, 0, 0)
        torque = Vec3(0, 0, 0)

        # If the camera-left key is pressed, move camera left.
        # If the camera-right key is pressed, move camera right.

        if inputState.isSet('cam-forward'):  force.setY( 1.0)
        if inputState.isSet('cam-backward'): force.setY(-1.0)
        if inputState.isSet('cam-left'):     force.setX(-1.0)
        if inputState.isSet('cam-right'):    force.setX( 1.0)
        if inputState.isSet('cam-turnleft'):  torque.setZ(1500)
        if inputState.isSet('cam-turnright'): torque.setZ(-1500)
        self.inst3.text = str(self.player.getH())

        force *= 2400.0
        force = render.getRelativeVector(self.player, force)
        self.player.node().setActive(True)
        self.player.node().applyCentralForce(force)
        self.player.node().applyTorque(torque)

        return task.cont

    # Define a procedure to rotate the camera with a motion controller.
    def spinCameraTask(self, task):
        if not self.motionControllerConnected:
            return Task.cont

        self.camera.setHpr(self.heading, self.pitch, self.roll)
        return Task.cont

app = MyApp()
app.run()
