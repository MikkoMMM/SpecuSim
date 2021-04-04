import struct
from time import sleep

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.stdpy import threading
from direct.task import Task
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletWorld
from panda3d.bullet import ZUp
from panda3d.bullet import get_bullet_version
from panda3d.core import BitMask32
from panda3d.core import PNMImage, Filename
from panda3d.core import SamplerState, TextNode
from panda3d.core import Vec3, load_prc_file_data, PStatClient, CullBinManager

from src.camera import CameraControl
from src.default_controls import setup_controls, interpret_controls
from src.default_gui import DefaultGUI
from src.getconfig import logger, settings, debug
from src.humanoid import Humanoid
from src.language_processing.nlp_manager import NLPManager
from src.menu import Menu
from src.utils import create_or_load_walk_map, create_shader_terrain_mesh


# from src.weapons.sword import Sword


class MyApp(ShowBase):
    def __init__(self):
        # Load some configuration variables, its important for this to happen
        # before the ShowBase is initialized
        load_prc_file_data("", """
            window-title SpecuSim - An Early Prototype

            # Specify whether textures should automatically be constrained to dimensions which are a power of 2 when they are loaded
            textures-power-2 none
            # If using a lot of shaders, apparently this is better
            gl-coordinate-system default

            # As an optimization, set this to the maximum number of cameras
            # or lights that will be rendering the terrain at any given time.
            stm-max-views 20

            # Further optimize the performance by reducing this to the max
            # number of chunks that will be visible at any given time.
            stm-max-chunk-count 2048

            texture-compression 1

            # The TransformState object cache is a performance hindrance for individually simulated body parts
            transform-cache 0

            bullet-filter-algorithm groups-mask
        """)

        # Initialize the showbase
        ShowBase.__init__(self)
        # In case window size would be at first detected incorrectly, buy a bit of time.
        base.graphicsEngine.render_frame()

        self.physics_debug = False
        self.nlp_debug = True  # Stuff that makes debugging natural language processing faster
        self.doppelganger_num = 0  # Actual number will be doppelganger_num^2-1 if odd and doppelganger_num^2 if even

        logger.debug(f"Using Bullet Physics version {get_bullet_version()}")

        if debug.getboolean("enable-pstats"):
            load_prc_file_data("", "task-timer-verbose 1")
            load_prc_file_data("", "pstats-tasks 1")
            PStatClient.connect()

        if settings.getboolean("enable-fps"):
            base.set_frame_rate_meter(True)

        self.menu_img = PNMImage(Filename("textures/menu.jpg"))

        self.main_menu = Menu(self.menu_img, aspect_ratio_keeping_scale=1)
        self.main_menu.change_button_style(PNMImage(Filename("textures/empty_button_52.png")), aspect_ratio_keeping_scale=2)
        self.main_menu.change_select_style(PNMImage(Filename("textures/select.png")), aspect_ratio_keeping_scale=2)
        self.main_menu.add_button("No Add-Ons", self.start_without_nlp, y=-0.1)
        self.main_menu.add_button("Language AI", self.start_with_nlp, y=0)
        self.main_menu.add_button("Exit Game", exit, y=0.1)
        self.main_menu.show_menu()

        # Increase camera FOV as well as the far plane
        self.camLens.set_fov(90)
        self.camLens.set_near_far(0.1, 50000)

        # Heightfield's height
        self.terrain_height = 25.0

        # Physics setup
        self.world = BulletWorld()
        # Currently no need for gravity.
        self.world.set_gravity(Vec3(0, 0, 0))

        # Collision groups:
        # 0: ground
        # 1: "ghost" body parts, for weapon hits
        # 2: reserved
        # 3: mutually colliding parts of characters
        self.world.set_group_collision_flag(1, 0, False)
        self.world.set_group_collision_flag(1, 1, False)
        self.world.set_group_collision_flag(3, 0, False)
        self.world.set_group_collision_flag(3, 1, False)
        self.world.set_group_collision_flag(3, 3, True)

        self.disable_mouse()

        self.terrain_bullet_node = BulletRigidBodyNode("terrainBodyNode")

        # To set Direct2D objects in front of others
        cull_manager = CullBinManager.getGlobalPtr()
        # According to the manual page linked-to below,
        # the highest-order standard bin has order 50,
        # so I'm assigning our new bin a sort order of 60.
        cull_manager.addBin("frontBin", cull_manager.BTFixed, 60)

        self.notice_text_obj = OnscreenText(text="", style=1, fg=(1, 1, 1, 1), scale=.05,
                                            shadow=(0, 0, 0, 1), parent=base.aspect2d,
                                            pos=(0.0, 0.3), align=TextNode.ACenter)
        self.notice_text_obj.setBin("frontBin", 1)

        self.nlp = False

        self.terrain_init_thread = threading.Thread(target=self.initialize_terrain, args=())
        self.terrain_init_thread.start()


    def start_without_nlp(self):
        self.terrain_init_thread.join()
        self.start_game()


    def start_with_nlp(self):
        from src.language_processing.load_model import load_language_model

        self.main_menu.hide_menu()
        self.terrain_init_thread.join()
        self.nlp = True
        self.generator_load_return = []
        load_language_model(self.notice_text_obj, self.menu_img, self.generator_load_return)
        taskMgr.add(self.wait_nlp_initialized, "nlp-init")


    def wait_nlp_initialized(self, task):
        if not self.generator_load_return:
            return task.cont
        self.npc1 = Humanoid(self.world, self.terrain_bullet_node, -2, 2)
        self.nlp_manager = NLPManager(self.generator_load_return[0], self.nlp_debug)
        self.start_game()
        return task.done


    def initialize_terrain(self):
        # Some terrain manipulations which weren't done at startup yet
        if self.physics_debug:
            # We have to use a smaller heightfield image for debugging
            elevation_img = PNMImage(Filename("worldmaps/debug_heightmap.png"))
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
            elevation_img = PNMImage(Filename("worldmaps/seed_16783_grayscale.png"))

            terrain = create_shader_terrain_mesh(elevation_img, self.terrain_height)

            # Wait for there to be a texture loader
            while not hasattr(self, 'loader'):
                sleep(0.01)

            # Set some texture on the terrain
            terrain_tex = self.loader.loadTexture("worldmaps/seed_16783_satellite.png")
            terrain_tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
            terrain_tex.set_anisotropic_degree(16)
            terrain.set_texture(terrain_tex)

        # Collision detection for the terrain
        if self.physics_debug:
            terrain_colshape = BulletHeightfieldShape(elevation_img, self.terrain_height, ZUp)
        else:
            terrain_colshape = BulletHeightfieldShape(
                create_or_load_walk_map("worldmaps/seed_16783_grayscale.png", "worldmaps/seed_16783_ocean.png"),
                self.terrain_height, ZUp)
        terrain_colshape.set_use_diamond_subdivision(True)

        self.terrain_bullet_node.add_shape(terrain_colshape)
        self.terrain_np = render.attach_new_node(self.terrain_bullet_node)
        self.terrain_np.set_collide_mask(BitMask32.bit(0))
        self.world.attach(self.terrain_np.node())

        return Task.done


    def start_game(self):
        self.main_menu.hide_menu()
        self.notice_text_obj.hide()

        self.player = Humanoid(self.world, self.terrain_bullet_node, 0, 0, debug=debug.getboolean("debug-joints"))

        self.doppelgangers = []
        for i in range(self.doppelganger_num):
            for j in range(self.doppelganger_num):
                if i == (self.doppelganger_num - 1) / 2 and j == (self.doppelganger_num - 1) / 2:
                    continue
                self.doppelgangers.append(
                    Humanoid(self.world, self.terrain_bullet_node, i * 2 - (self.doppelganger_num - 1),
                             j * 2 - (self.doppelganger_num - 1)))

        self.gui = DefaultGUI(text_input_func=self.player_say)

        self.camera.reparent_to(self.player.lower_torso)

        cam_control = CameraControl(camera, self.mouseWatcherNode)
        cam_control.attach_to(self.player.lower_torso)

        self.taskMgr.add(cam_control.move_camera, "MoveCameraTask")

        self.accept("wheel_down", cam_control.wheel_down)
        self.accept("wheel_up", cam_control.wheel_up)

        setup_controls()

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")


    def player_say(self, text):
        self.gui.text_field.enterText('')
        logger.debug(f"The player said: {text}")
        self.player.say(text)
        you_say = f"You say: \"{text}\""
        if self.nlp:
            self.nlp_manager.new_speech_task(self.npc1, you_say)
        self.gui.focus_out_text_field()


    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.get_dt()

        self.world.do_physics(dt, 5, 1.0 / 80.0)

        # Define controls
        if self.gui.text_field['focus']:
            interpret_controls(self.player, stand_still=True)
        else:
            interpret_controls(self.player)

        if self.nlp:
            data = self.player.get_compressed_state()
            uncompressed = struct.unpack(self.player.get_state_format(), data)
            self.npc1.set_state_shifted(*uncompressed, 2, 0)
            self.npc1.stand_still()
            self.nlp_manager.update()

        #        self.player.setRightHandHpr(self.heading, self.pitch, self.roll)

        return task.cont


app = MyApp()
app.run()
