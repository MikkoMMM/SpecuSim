from src.motioncontrols.fusion import Fusion, DeltaT
from src.humanoid2 import Humanoid
from math import pi, sin, cos, radians, sqrt, degrees

from direct.showbase.InputStateGlobal import inputState
from direct.gui.DirectGui import DirectFrame
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import Vec3, Vec4, ShaderTerrainMesh, Shader, load_prc_file_data, PStatClient
from panda3d.core import SamplerState, TextNode
from panda3d.core import Texture, Mat4
from panda3d.core import PNMImage, Filename
from direct.task import Task
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import getBulletVersion
from panda3d.core import BitMask32, TransformState, NodePath, PandaNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import ZUp
from src.utils import angleDiff
from src.menu import Menu
from src.weapons.sword import Sword


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

            # The TransformState object cache is a performance hindrance for individually simulated body parts
            transform-cache 0

            bullet-filter-algorithm groups-mask

            # These are enabled for debugging purposes. For production use, disable them.
            task-timer-verbose 1
            pstats-tasks 1
#            direct-gui-edit 1
        """)

        # Initialize the showbase
        ShowBase.__init__(self)
        # In case window size would be at first detected incorrectly, buy a bit of time.
        base.graphicsEngine.renderFrame() 

        self.performanceAnalysis = True # Enable pstat support and show frame rate
        self.physicsDebug = False        # Show wireframes for the physics objects.
        self.debugMessages = False       # Some extraneous information

        if self.debugMessages:
            print("Using Bullet Physics version ", getBulletVersion())
            print()

        if self.performanceAnalysis:
            base.setFrameRateMeter(True)
            PStatClient.connect()

        self.doppelgangerNum = 0      # Actual number will be doppelgangerNum^2-1

        # For calculating motion controller orientation
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        #self.deltat = DeltaT(timediff)
        #self.fuse = Fusion(10, timediff) # A fairly large GyroMeansError so erroneous values are quickly resolved

        self.menu = Menu(self)
        self.menu.showMenu()

        # Increase camera FOV as well as the far plane
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)
        
        #Heightfield's height
        self.height = 25.0

        self.motionControllerAccuracy = 40 # The motion controller's orientation is to be updated 100 times this number per second

        # Physics setup
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        #Collision groups:
        # 0: ground
        # 1: "ghost" body parts, for weapon hits
        # 2: feet
        # 3: mutually colliding parts of characters
        self.world.setGroupCollisionFlag(1, 0, False)
        self.world.setGroupCollisionFlag(1, 1, False)
        self.world.setGroupCollisionFlag(2, 0, True)
        self.world.setGroupCollisionFlag(2, 1, False)
        self.world.setGroupCollisionFlag(2, 2, False)
        self.world.setGroupCollisionFlag(3, 0, False)
        self.world.setGroupCollisionFlag(3, 1, False)
        self.world.setGroupCollisionFlag(3, 2, False)
        self.world.setGroupCollisionFlag(3, 3, True)

        self.motionControllerConnected = False
        self.disableMouse()
        
       
        if self.physicsDebug:
            # We have to use a smaller heightfield image for debugging
            elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale_tiny.png'))
            self.worldNP = render.attachNewNode('World')
            self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
            self.debugNP.node().showNormals(True)
            self.debugNP.node().showBoundingBoxes(False)
            self.debugNP.node().showConstraints(True)
            self.debugNP.show()
            self.world.setDebugNode(self.debugNP.node())
        else:
            # Set a heightfield, the heightfield should be a 16-bit png and
            # have a quadratic size of a power of two.
            elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale.png'))

        elevation_img_size = elevation_img.getXSize()
        elevation_img_offset = elevation_img_size / 2.0
        heightfield = Texture("heightfield")
        heightfield.load(elevation_img)
        heightfield.wrap_u = SamplerState.WM_clamp
        heightfield.wrap_v = SamplerState.WM_clamp

        # Construct the terrain
        self.terrain_node = ShaderTerrainMesh()
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
        terrain_colshape = BulletHeightfieldShape(elevation_img, self.height, ZUp)
        terrain_colshape.setUseDiamondSubdivision(True)

        self.terrainBulletNode = BulletRigidBodyNode("terrainBodyNode")
        self.terrainBulletNode.addShape(terrain_colshape)
        self.terrainNp0 = render.attachNewNode(self.terrainBulletNode)
        self.terrainNp0.setCollideMask(BitMask32.bit(0))
        #self.terrainNp0.setCollideMask(BitMask32.bit(1))
        self.terrainNp0.setPos(0, 0, 0)


    def startGame(self):
        self.menu.hideMenu()
        self.world.attach(self.terrainNp0.node())
#        self.player = Humanoid(self.render, self.world, self.terrainBulletNode, Vec3(0,0,-8), Vec3(0,0,0))
        self.player = Humanoid(self.render, self.world, self.terrainBulletNode, 0, 0, debug=self.physicsDebug)
        
        self.doppelgangers = []
        for i in range(self.doppelgangerNum):
            for j in range(self.doppelgangerNum):
                if i == (self.doppelgangerNum-1)/2 and j == (self.doppelgangerNum-1)/2: continue
                self.doppelgangers.append(Humanoid(self.render, self.world, self.terrainBulletNode, i-(self.doppelgangerNum-1)/2, j-(self.doppelgangerNum-1)/2))


        self.camera.reparentTo(self.player.lowerTorso)
        self.camera.setPos(0, -10, 0)
        self.oldCameraZ = self.camera.getZ(self.render)

#        self.weapon = Sword(self.render, self.world, self.player.lowerTorso)
#        self.player.grabRight(self.weapon.getAttachmentInfo())

        self.inst1 = addInstructions(0.06, "[WASD]: Move")
        self.inst2 = addInstructions(0.12, "[QE]: Rotate")
        self.inst2 = addInstructions(0.18, "[+-]: Change speed")
        self.inst3 = addInstructions(0.24, "Middle mouse button: Rotate camera")
        self.inst4 = addInstructions(0.30, "Right mouse button: Adjust zoom")
        self.inst5 = addInstructions(0.36, "")
        self.inst6 = addInstructions(0.42, "")
        self.inst7 = addInstructions(0.48, "")

        self.accept('mouse1',self.disableMouse)
        self.accept('mouse2',self.reEnableMouse)
        self.accept('mouse3',self.reEnableMouse)
        self.accept('f1', self.toggleWireframe)
        self.accept('f2', self.toggleTexture)
        inputState.watchWithModifiers('forward', 'w')
        inputState.watchWithModifiers('left', 'a')
        inputState.watchWithModifiers('backward', 's')
        inputState.watchWithModifiers('right', 'd')
        inputState.watchWithModifiers('turnleft', 'q')
        inputState.watchWithModifiers('turnright', 'e')
        inputState.watchWithModifiers('speedup', '+')
        inputState.watchWithModifiers('speeddown', '-')

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")
        if self.debugMessages:
            self.render.analyze()


    def reEnableMouse(self):
        base.disableMouse()
        mat = Mat4(self.camera.getMat())
        mat.invertInPlace()
        base.mouseInterfaceNode.setMat(mat)
        base.enableMouse()

    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.getDt()

        self.world.doPhysics(dt, 5, 1.0/80.0)

        # Define controls
        stepping = False


        if inputState.isSet('forward'):
            if inputState.isSet('left'):
                self.player.walkInDir(-45)
                for doppelganger in self.doppelgangers:
                    doppelganger.walkInDir(-45)
            elif inputState.isSet('right'):
                self.player.walkInDir(45)
                for doppelganger in self.doppelgangers:
                    doppelganger.walkInDir(45)
            else:
                self.player.walkInDir(0)
                for doppelganger in self.doppelgangers:
                    doppelganger.walkInDir(0)
            stepping = True
        elif inputState.isSet('backward'):
            if inputState.isSet('left'):
                self.player.walkInDir(-135)
                for doppelganger in self.doppelgangers:
                    doppelganger.walkInDir(-135)
            elif inputState.isSet('right'):
                self.player.walkInDir(135)
                for doppelganger in self.doppelgangers:
                    doppelganger.walkInDir(135)
            else:
                self.player.walkInDir(180)
                for doppelganger in self.doppelgangers:
                    doppelganger.walkInDir(180)
            stepping = True
        elif inputState.isSet('left'):
            self.player.walkInDir(-90)
            for doppelganger in self.doppelgangers:
                doppelganger.walkInDir(-90)
            stepping = True
        elif inputState.isSet('right'):
            self.player.walkInDir(90)
            for doppelganger in self.doppelgangers:
                doppelganger.walkInDir(90)
            stepping = True

        if not stepping:
            self.player.standStill()
            for doppelganger in self.doppelgangers:
                doppelganger.standStill()

        if inputState.isSet('turnleft'):
            self.player.turnLeft()
            for doppelganger in self.doppelgangers:
                doppelganger.turnLeft()
        if inputState.isSet('turnright'):
            self.player.turnRight()
            for doppelganger in self.doppelgangers:
                doppelganger.turnRight()

        if inputState.isSet('speedup'):
            self.player.speedUp()
            for doppelganger in self.doppelgangers:
                doppelganger.speedUp()
        if inputState.isSet('speeddown'):
            self.player.slowDown()
            for doppelganger in self.doppelgangers:
                doppelganger.slowDown()

        self.inst5.text = "Speed " + str(round(sqrt(pow(self.player.lowerTorso.node().getLinearVelocity()[0], 2) + pow(self.player.lowerTorso.node().getLinearVelocity()[1], 2)),2)) + " / " + str(round(self.player.walkSpeed,1)) + " m/s"
#        self.inst6.text = "H" + str(int(self.heading)) + " P" + str(int(self.pitch))
#        self.inst7.text = str(self.player.leftLeg.thigh.getH()) + " " + str(self.player.lowerTorso.getH())

        
#        if self.motionControllerConnected:
#        self.player.setRightHandHpr(self.heading, self.pitch, self.roll)

        # Roll in the camera would only serve to confuse
        self.camera.setR(0)
        # Reduce camera's bounciness
        if abs(self.camera.getZ(self.render)-self.oldCameraZ) < 0.1:
            self.camera.setZ(self.render, self.oldCameraZ)
        else:
            self.camera.setZ(self.render, (self.oldCameraZ*2 + self.camera.getZ(self.render))/3)
        self.oldCameraZ = self.camera.getZ(self.render)

        self.player.updateHeading()
        for doppelganger in self.doppelgangers:
            doppelganger.updateHeading()

        return task.cont

app = MyApp()
app.run()
