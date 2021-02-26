from src.motioncontrols.fusion import Fusion, DeltaT
from src.motioncontrols.wiimote import Wiimote
from src.humanoid import Humanoid
from math import pi, sin, cos, radians, sqrt, degrees

from direct.showbase.InputStateGlobal import inputState
from direct.gui.DirectGui import DirectFrame
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import Vec3, Vec4, ShaderTerrainMesh, Shader, load_prc_file_data, PStatClient
from panda3d.core import SamplerState, TextNode, TextureStage, TP_normal
from panda3d.core import CardMaker, Texture, Mat4
from panda3d.core import PNMImage, Filename
from direct.task import Task
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import getBulletVersion
from panda3d.core import BitMask32, TransformState, Point3, NodePath, PandaNode, RigidBodyCombiner
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import ZUp
from src.utils import angleDiff


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

            bullet-filter-algorithm groups-mask
            task-timer-verbose 1
            pstats-tasks 1
            transform-cache 0 # The TransformState object cache is a performance hindrance for individually simulated body parts
        """)

        # Initialize the showbase
        ShowBase.__init__(self)

        # Performance analysis
        base.setFrameRateMeter(True)
        PStatClient.connect()

        self.physicsThreads = 0 # EXPERIMENTAL! 0 for disabling the functionality, 4 for 4 physics threads.
        doppelgangerNum = 0 # Actual number will be doppelgangerNum^2-1

        # Increase camera FOV as well as the far plane
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)
        
        #Heightfield's height
        self.height = 25.0

        self.motionControllerAccuracy = 40 # The motion controller's orientation is to be updated 100 times this number per second
        self.stepTime = 0.8 # How long a character's step will take by default

        # Physics setup
        self.worlds = []
        if self.physicsThreads == 0:
            end = 1
        else:
            end = self.physicsThreads
        for i in range(end):
            world = BulletWorld()
            world.setGravity(Vec3(0, 0, -9.81))
            root = NodePath(PandaNode("world root"))

            #Collision groups:
            # 0: ground
            # 1: "normal" body parts
            # 2: feet
            world.setGroupCollisionFlag(0, 1, False)
            world.setGroupCollisionFlag(1, 1, False)
            world.setGroupCollisionFlag(2, 0, True)
            world.setGroupCollisionFlag(2, 1, False)
            world.setGroupCollisionFlag(2, 2, False)

            self.worlds.append((world, root))

        self.motionControllerConnected = False
        self.disableMouse()
        
       
        # These would show wireframes for the physics objects.
        # However, the normal heightfield is too large for this to work. Switch to a smaller one if you wish to visually debug.
        '''
        self.worldNP = render.attachNewNode('World')
        self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.node().showNormals(True)
        self.debugNP.node().showBoundingBoxes(False)
        self.debugNP.node().showConstraints(True)
        self.debugNP.show()
        self.world.setDebugNode(self.debugNP.node())
        '''
        # Construct the terrain
        self.terrain_node = ShaderTerrainMesh()

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale.png'))
        elevation_img_size = elevation_img.getXSize()
        elevation_img_offset = elevation_img_size / 2.0
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
        terrain_colshape = BulletHeightfieldShape(elevation_img, self.height, ZUp)
        terrain_colshape.setUseDiamondSubdivision(True)

        self.terrainBulletNode0 = BulletRigidBodyNode("terrainBodyNode0")
        self.terrainBulletNode0.addShape(terrain_colshape)
        self.terrainNp0 = render.attachNewNode(self.terrainBulletNode0)
        self.terrainNp0.setCollideMask(BitMask32.bit(0))
        #self.terrainNp0.setCollideMask(BitMask32.bit(1))
        self.terrainNp0.setPos(0, 0, 0)
        if self.physicsThreads == 4:
            self.terrainBulletNode1 = BulletRigidBodyNode("terrainBodyNode1")
            self.terrainBulletNode1.addShape(terrain_colshape)
            self.terrainNp1 = render.attachNewNode(self.terrainBulletNode1)
            self.terrainNp1.setCollideMask(BitMask32.bit(0))
            self.terrainNp1.setPos(0, 0, 0)
            self.terrainBulletNode2 = BulletRigidBodyNode("terrainBodyNode2")
            self.terrainBulletNode2.addShape(terrain_colshape)
            self.terrainNp2 = render.attachNewNode(self.terrainBulletNode2)
            self.terrainNp2.setCollideMask(BitMask32.bit(0))
            self.terrainNp2.setPos(0, 0, 0)
            self.terrainBulletNode3 = BulletRigidBodyNode("terrainBodyNode3")
            self.terrainBulletNode3.addShape(terrain_colshape)
            self.terrainNp3 = render.attachNewNode(self.terrainBulletNode3)
            self.terrainNp3.setCollideMask(BitMask32.bit(0))
            self.terrainNp3.setPos(0, 0, 0)


        world, root = self.worlds[0]
        self.player = Humanoid(self.render, world, self.terrainBulletNode0, Vec3(0,0,-8), Vec3(0,0,0))
        
        self.doppelgangers = []
        for i in range(doppelgangerNum):
            for j in range(doppelgangerNum):
                if self.physicsThreads == 0:
                    world, root = self.worlds[0]
                else:
                    world, root = self.worlds[i%self.physicsThreads]
                if i == (doppelgangerNum-1)/2 and j == (doppelgangerNum-1)/2: continue
                self.doppelgangers.append(Humanoid(self.render, world, self.terrainBulletNode0, Vec3(i-(doppelgangerNum-1)/2,j-(doppelgangerNum-1)/2,0), Vec3(0,0,0)))
        

        self.camera.reparentTo(self.player.lowerTorso)
#        self.camera.setPos(0, -10, 40)
        self.camera.setPos(0, -10, 0)
#        self.camera.lookAt(self.player.chest, 0, 5, 0)

        # For calculating motion controller orientation
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        self.deltat = DeltaT(timediff)
        self.fuse = Fusion(2, timediff)

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

        # Connect, calibrate and start reading information from a motion controller
#        self.motionController = Wiimote(self)

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")
        taskMgr.add(self.spinCameraTask, "SpinCameraTask")
        self.addCollisionNPToWorld(0, self.terrainNp0)
        if self.physicsThreads > 0:
            physicsChain = taskMgr.setupTaskChain('physicsChain', numThreads = 4, threadPriority = None, frameSync = True)
            taskMgr.add(self.physics0, 'physics0', taskChain = 'physicsChain')
            self.addCollisionNPToWorld(0, self.terrainNp0)
            if self.physicsThreads == 4:
                taskMgr.add(self.physics1, 'physics1', taskChain = 'physicsChain')
                taskMgr.add(self.physics2, 'physics2', taskChain = 'physicsChain')
                taskMgr.add(self.physics3, 'physics3', taskChain = 'physicsChain')
                self.addCollisionNPToWorld(1, self.terrainNp1)
                self.addCollisionNPToWorld(2, self.terrainNp2)
                self.addCollisionNPToWorld(3, self.terrainNp3)
        self.render.analyze()



    # This may not be the ideal way to do the following;
    # I'm doing it this way for simplicity and example
    def addCollisionNPToWorld(self, worldIndex, nodePath):
        world, root = self.worlds[worldIndex]
#        nodePath.setCollideMask(BitMask32.bit(collidemask))
#        nodePath.reparentTo(root)
        world.attach(nodePath.node())


    def reEnableMouse(self):
        base.disableMouse()
        mat = Mat4(self.camera.getMat())
        mat.invertInPlace()
        base.mouseInterfaceNode.setMat(mat)
        base.enableMouse()

    def physics0(self, task):
        # Get the time that elapsed since last frame.
        dt = globalClock.getDt()

        # Do a physics update.
        # Choosing smaller substeps will make the simulation more realistic,
        # but performance will decrease too. Smaller substeps also reduce jitter.
        world, root = self.worlds[0]
        world.doPhysics(dt, 10, 1.0/125.0)
        return task.cont

    def physics1(self, task):
        # Get the time that elapsed since last frame.
        dt = globalClock.getDt()

        # Do a physics update.
        # Choosing smaller substeps will make the simulation more realistic,
        # but performance will decrease too. Smaller substeps also reduce jitter.
        world, root = self.worlds[1]
        world.doPhysics(dt, 10, 1.0/125.0)
        return task.cont

    def physics2(self, task):
        # Get the time that elapsed since last frame.
        dt = globalClock.getDt()

        # Do a physics update.
        # Choosing smaller substeps will make the simulation more realistic,
        # but performance will decrease too. Smaller substeps also reduce jitter.
        world, root = self.worlds[2]
        world.doPhysics(dt, 10, 1.0/125.0)
        return task.cont

    def physics3(self, task):
        # Get the time that elapsed since last frame.
        dt = globalClock.getDt()

        # Do a physics update.
        # Choosing smaller substeps will make the simulation more realistic,
        # but performance will decrease too. Smaller substeps also reduce jitter.
        world, root = self.worlds[3]
        world.doPhysics(dt, 10, 1.0/125.0)
        return task.cont

    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.getDt()

        if self.physicsThreads == 0:
            world, root = self.worlds[0]
            world.doPhysics(dt, 5, 1.0/80.0)
            
        # Define controls
        stepping = False

        if inputState.isSet('forward'):
            if inputState.isSet('left'):
                self.player.takeStep(self.stepTime, -45)
                for doppelganger in self.doppelgangers:
                    doppelganger.takeStep(self.stepTime, -45)
            elif inputState.isSet('right'):
                self.player.takeStep(self.stepTime, 45)
                for doppelganger in self.doppelgangers:
                    doppelganger.takeStep(self.stepTime, 45)
            else:
                self.player.takeStep(self.stepTime, 0)
                for doppelganger in self.doppelgangers:
                    doppelganger.takeStep(self.stepTime, 0)
            stepping = True
        elif inputState.isSet('backward'):
            if inputState.isSet('left'):
                self.player.takeStep(self.stepTime, -135)
                for doppelganger in self.doppelgangers:
                    doppelganger.takeStep(self.stepTime, -135)
            elif inputState.isSet('right'):
                self.player.takeStep(self.stepTime, 135)
                for doppelganger in self.doppelgangers:
                    doppelganger.takeStep(self.stepTime, 135)
            else:
                self.player.takeStep(self.stepTime, 180)
                for doppelganger in self.doppelgangers:
                    doppelganger.takeStep(self.stepTime, 180)
            stepping = True
        elif inputState.isSet('left'):
            self.player.takeStep(self.stepTime, -90)
            for doppelganger in self.doppelgangers:
                doppelganger.takeStep(self.stepTime, -90)
            stepping = True
        elif inputState.isSet('right'):
            self.player.takeStep(self.stepTime, 90)
            for doppelganger in self.doppelgangers:
                doppelganger.takeStep(self.stepTime, 90)
            stepping = True
        if not stepping:
            self.player.standStill()
            for doppelganger in self.doppelgangers:
                doppelganger.standStill()
        if inputState.isSet('turnleft'):
            self.player.turnLeft(dt)
            for doppelganger in self.doppelgangers:
                doppelganger.turnLeft(dt)
        if inputState.isSet('turnright'):
            self.player.turnRight(dt)
            for doppelganger in self.doppelgangers:
                doppelganger.turnRight(dt)
        if inputState.isSet('speedup'):
            self.stepTime -= dt*1.20
            if self.stepTime < 0:
                self.stepTime = dt
        if inputState.isSet('speeddown'):  self.stepTime += dt*1.20
        
        self.inst5.text = str(self.stepTime) + " " + str(sqrt(pow(self.player.chest.node().getLinearVelocity()[0], 2) + pow(self.player.chest.node().getLinearVelocity()[1], 2)))
        if self.player.inverted:
            self.inst6.text = "True"
        else:
            self.inst6.text = "False"
#        self.inst7.text = str(self.player.leftLeg.thigh.getH()) + " " + str(self.player.lowerTorso.getH())

        self.camera.setR(0)

        return task.cont

    # Define a procedure to rotate the camera with a motion controller.
    def spinCameraTask(self, task):
        if not self.motionControllerConnected:
            return Task.cont

        self.camera.setHpr(self.heading, self.pitch, self.roll)
        return Task.cont

print("Using Bullet Physics version ", getBulletVersion())
print()
app = MyApp()
app.run()
