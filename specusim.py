from src.motioncontrols.fusion import Fusion, DeltaT
from src.humanoid2 import Humanoid
from math import pi, sin, cos, radians, sqrt, degrees

from direct.showbase.InputStateGlobal import inputState
from direct.gui.DirectGui import DirectFrame, DirectLabel
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
from panda3d.bullet import get_bullet_version
from panda3d.core import BitMask32, TransformState, NodePath, PandaNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import ZUp
from src.menu import Menu
#from src.weapons.sword import Sword


def timediff(time1, time2):
    return (time1-time2)


# Function to put instructions on the screen.
def add_instructions(pos, msg):
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
        """)

        # Initialize the showbase
        ShowBase.__init__(self)
        # In case window size would be at first detected incorrectly, buy a bit of time.
        base.graphicsEngine.render_frame() 

        self.gui = True                 # A toggle for the GUI for testing puposes
        self.performance_analysis = True # Enable pstat support and show frame rate
        self.physics_debug = True        # Show wireframes for the physics objects.
        self.debug_messages = False       # Some extraneous information

        if self.debug_messages:
            print("Using Bullet Physics version ", get_bullet_version())
            print()

        if self.performance_analysis:
            load_prc_file_data("", "task-timer-verbose 1")
            load_prc_file_data("", "pstats-tasks 1")

            base.set_frame_rate_meter(True)
            PStatClient.connect()

        self.doppelganger_num = 0      # Actual number will be doppelganger_num^2-1 if odd and doppelganger_num^2 if even

        # For calculating motion controller orientation
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        #self.deltat = DeltaT(timediff)
        #self.fuse = Fusion(10, timediff) # A fairly large GyroMeansError so erroneous values are quickly resolved

        self.menu = Menu(self)
        self.menu.show_menu()

        # Increase camera FOV as well as the far plane
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)
        
        #Heightfield's height
        self.height = 25.0

        # Physics setup
        self.world = BulletWorld()
        # The custom ground collision doesn't go well along with gravity, but some aesthetics depend on it.
        self.world.set_gravity(Vec3(0, 0, -9.81))

        #Collision groups:
        # 0: ground
        # 1: "ghost" body parts, for weapon hits
        # 2: feet
        # 3: mutually colliding parts of characters
        self.world.set_group_collision_flag(1, 0, False)
        self.world.set_group_collision_flag(1, 1, False)
        self.world.set_group_collision_flag(2, 0, True)
        self.world.set_group_collision_flag(2, 1, False)
        self.world.set_group_collision_flag(2, 2, False)
        self.world.set_group_collision_flag(3, 0, False)
        self.world.set_group_collision_flag(3, 1, False)
        self.world.set_group_collision_flag(3, 2, False)
        self.world.set_group_collision_flag(3, 3, True)

        self.disable_mouse()
        
       
        if self.physics_debug:
            # We have to use a smaller heightfield image for debugging
            elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale_tiny.png'))
            self.world_np = render.attach_new_node('World')
            self.debug_np = self.world_np.attach_new_node(BulletDebugNode('Debug'))
            self.debug_np.node().show_normals(True)
            self.debug_np.node().show_bounding_boxes(False)
            self.debug_np.node().show_constraints(True)
            self.debug_np.show()
            self.world.set_debug_node(self.debug_np.node())
        else:
            # Set a heightfield, the heightfield should be a 16-bit png and
            # have a quadratic size of a power of two.
            elevation_img = PNMImage(Filename('worldmaps/seed_16783_grayscale.png'))

        elevation_img_size = elevation_img.get_x_size()
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
        terrain_colshape.set_use_diamond_subdivision(True)

        self.terrain_bullet_node = BulletRigidBodyNode("terrainBodyNode")
        self.terrain_bullet_node.add_shape(terrain_colshape)
        self.terrain_np = render.attach_new_node(self.terrain_bullet_node)
        self.terrain_np.set_collide_mask(BitMask32.bit(0))
        self.terrain_np.set_pos(0, 0, 0)
        self.world.attach(self.terrain_np.node())

    def start_with_nlp(self):
        self.npc1 = Humanoid(self.render, self.world, self.terrain_bullet_node, -2, 2)

        self.speech_bubble=DirectLabel(parent=self.npc1.lower_torso, text="'Ello, 'ello, 'ello!", text_wordwrap=10,
                        relief = None, text_scale=(.5,.5),
                        pos = (0,0,2),
                        frameColor=(.3,.2,.1,.5),
                        text_frame=(0,0,0,1),
                        text_bg=(1,1,1,0.4))
        self.speech_bubble.component('text0').textNode.set_card_decal(1)
#        self.speech_bubble['text'] = "Why, hello there!"
        self.speech_bubble.set_billboard_point_eye()

        self.start_game()


    def start_game(self):
        self.menu.hide_menu()
#        self.player = Humanoid(self.render, self.world, self.terrain_bullet_node, Vec3(0,0,-8), Vec3(0,0,0))
        self.player = Humanoid(self.render, self.world, self.terrain_bullet_node, 0, 0, debug=self.physics_debug)
        
        self.doppelgangers = []
        for i in range(self.doppelganger_num):
            for j in range(self.doppelganger_num):
                if i == (self.doppelganger_num-1)/2 and j == (self.doppelganger_num-1)/2: continue
                self.doppelgangers.append(Humanoid(self.render, self.world, self.terrain_bullet_node, i-(self.doppelganger_num-1)/2, j-(self.doppelganger_num-1)/2))


        self.camera.reparent_to(self.player.lower_torso)
        self.camera.set_pos(0, -10, 0)
        self.old_camera_z = self.camera.getZ(self.render)

#        self.weapon = Sword(self.render, self.world, self.player.lower_torso)
#        self.player.grabRight(self.weapon.getAttachmentInfo())

        self.inst1 = add_instructions(0.06, "[WASD]: Move")
        self.inst2 = add_instructions(0.12, "[QE]: Rotate")
        self.inst2 = add_instructions(0.18, "[+-]: Change speed")
        self.inst3 = add_instructions(0.24, "Middle mouse button: Rotate camera")
        self.inst4 = add_instructions(0.30, "Right mouse button: Adjust zoom")
        self.inst5 = add_instructions(0.36, "")
        self.inst6 = add_instructions(0.42, "")
        self.inst7 = add_instructions(0.48, "")

        self.accept('mouse1',self.disable_mouse)
        self.accept('mouse2',self.re_enable_mouse)
        self.accept('mouse3',self.re_enable_mouse)
        self.accept('f1', self.toggle_wireframe)
        self.accept('f2', self.toggle_texture)
        inputState.watch_with_modifiers('forward', 'w')
        inputState.watch_with_modifiers('left', 'a')
        inputState.watch_with_modifiers('backward', 's')
        inputState.watch_with_modifiers('right', 'd')
        inputState.watch_with_modifiers('turnleft', 'q')
        inputState.watch_with_modifiers('turnright', 'e')
        inputState.watch_with_modifiers('speedup', '+')
        inputState.watch_with_modifiers('speeddown', '-')

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")
        if self.debug_messages:
            self.render.analyze()


    def re_enable_mouse(self):
        base.disable_mouse()
        mat = Mat4(self.camera.get_mat())
        mat.invert_in_place()
        base.mouseInterfaceNode.set_mat(mat)
        base.enable_mouse()

    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.get_dt()

        self.world.do_physics(dt, 5, 1.0/80.0)

        # Define controls
        stepping = False


        if inputState.is_set('forward'):
            if inputState.is_set('left'):
                self.player.walk_in_dir(-45)
                for doppelganger in self.doppelgangers:
                    doppelganger.walk_in_dir(-45)
            elif inputState.is_set('right'):
                self.player.walk_in_dir(45)
                for doppelganger in self.doppelgangers:
                    doppelganger.walk_in_dir(45)
            else:
                self.player.walk_in_dir(0)
                for doppelganger in self.doppelgangers:
                    doppelganger.walk_in_dir(0)
            stepping = True
        elif inputState.is_set('backward'):
            if inputState.is_set('left'):
                self.player.walk_in_dir(-135)
                for doppelganger in self.doppelgangers:
                    doppelganger.walk_in_dir(-135)
            elif inputState.is_set('right'):
                self.player.walk_in_dir(135)
                for doppelganger in self.doppelgangers:
                    doppelganger.walk_in_dir(135)
            else:
                self.player.walk_in_dir(180)
                for doppelganger in self.doppelgangers:
                    doppelganger.walk_in_dir(180)
            stepping = True
        elif inputState.is_set('left'):
            self.player.walk_in_dir(-90)
            for doppelganger in self.doppelgangers:
                doppelganger.walk_in_dir(-90)
            stepping = True
        elif inputState.is_set('right'):
            self.player.walk_in_dir(90)
            for doppelganger in self.doppelgangers:
                doppelganger.walk_in_dir(90)
            stepping = True

        if not stepping:
            self.player.stand_still()
            for doppelganger in self.doppelgangers:
                doppelganger.stand_still()

        if inputState.is_set('turnleft'):
            self.player.turn_left()
            for doppelganger in self.doppelgangers:
                doppelganger.turn_left()
        if inputState.is_set('turnright'):
            self.player.turn_right()
            for doppelganger in self.doppelgangers:
                doppelganger.turn_right()

        if inputState.is_set('speedup'):
            self.player.speed_up()
            for doppelganger in self.doppelgangers:
                doppelganger.speed_up()
        if inputState.is_set('speeddown'):
            self.player.slow_down()
            for doppelganger in self.doppelgangers:
                doppelganger.slow_down()

        self.inst5.text = "Speed " + str(round(sqrt(pow(self.player.lower_torso.node().get_linear_velocity()[0], 2) + pow(self.player.lower_torso.node().get_linear_velocity()[1], 2)),2)) + " / " + str(round(self.player.walk_speed,1)) + " m/s"

        if hasattr(self, 'npc1'):
            self.npc1.stand_still()
            self.npc1.update_heading()
            self.npc1.update_heading()
#        self.speech_bubble['text'] += "."
#        if len(self.speech_bubble['text']) > 30:
#            self.speech_bubble['text'] = ""

#        self.player.setRightHandHpr(self.heading, self.pitch, self.roll)

        # Roll in the camera would only serve to confuse
        self.camera.setR(0)
        # Reduce camera's bounciness
        if abs(self.camera.getZ(self.render)-self.old_camera_z) < 0.1:
            self.camera.setZ(self.render, self.old_camera_z)
        else:
            self.camera.setZ(self.render, (self.old_camera_z*2 + self.camera.getZ(self.render))/3)
        self.old_camera_z = self.camera.getZ(self.render)

        self.player.update_heading()
        for doppelganger in self.doppelgangers:
            doppelganger.update_heading()

        return task.cont

app = MyApp()
app.run()
