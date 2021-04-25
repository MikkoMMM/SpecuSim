import struct
from time import sleep

from direct.gui.OnscreenText import OnscreenText
from direct.stdpy import threading
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletWorld
from panda3d.bullet import ZUp
from panda3d.core import BitMask32
from panda3d.core import PNMImage, Filename
from panda3d.core import SamplerState, TextNode
from panda3d.core import Vec3, CullBinManager

from src.camera import CameraControl
from src.default_controls import setup_controls, interpret_controls
from src.gui.default_gui import DefaultGUI
from src.getconfig import logger, debug
from src.humanoid import Humanoid
from src.language_processing.load_model import load_language_model
from src.language_processing.nlp_manager import NLPManager
from src.utils import create_or_load_walk_map, create_and_texture_terrain
from panda3d.core import TextPropertiesManager, TextProperties


class Game:
    def __init__(self):
        # Increase camera FOV as well as the far plane
        base.camLens.set_fov(90)
        base.camLens.set_near_far(0.1, 50000)

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

        base.disable_mouse()

        self.terrain_bullet_node = BulletRigidBodyNode("terrainBodyNode")

        # To set Direct2D objects in front of others
        cull_manager = CullBinManager.getGlobalPtr()
        # The highest-order standard bin has a sort order of 50
        cull_manager.addBin("frontBin", cull_manager.BTFixed, 60)

        self.notice_text_obj = OnscreenText(text="", style=1, fg=(1, 1, 1, 1), scale=.05,
                                            shadow=(0, 0, 0, 1), parent=base.aspect2d,
                                            pos=(0.0, 0.3), align=TextNode.ACenter)
        self.notice_text_obj.setBin("frontBin", 1)

        self.terrain_init_thread = threading.Thread(target=self.initialize_terrain, args=())
        self.terrain_init_thread.start()

        self.generator_load_return = []
        load_language_model(self.notice_text_obj, PNMImage(Filename("textures/menu.jpg")), self.generator_load_return)
        taskMgr.add(self.wait_nlp_initialized, "nlp-init")


    def wait_nlp_initialized(self, task):
        if not self.generator_load_return:
            return task.cont
        # Characters must be created only after the terrain_bullet_node has been finalized
        self.terrain_init_thread.join()
        self.npc1 = Humanoid(self.world, self.terrain_bullet_node, -2, 2)
        self.nlp_manager = NLPManager(self.generator_load_return[0])
        self.start_game()
        return task.done


    def initialize_terrain(self):
        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        elevation_img = PNMImage(Filename("worldmaps/seed_16783_grayscale.png"))
        texture_img = PNMImage(Filename("worldmaps/seed_16783_satellite.png"))
        create_and_texture_terrain(elevation_img, self.terrain_height, texture_img)

        # Collision detection for the terrain. Preferably the image should have a size 1 pixel taller and wider than elevation_img.
        terrain_colshape = BulletHeightfieldShape(
            create_or_load_walk_map("worldmaps/seed_16783_grayscale.png", "worldmaps/seed_16783_ocean.png"),
            self.terrain_height, ZUp)
        terrain_colshape.set_use_diamond_subdivision(True)

        self.terrain_bullet_node.add_shape(terrain_colshape)
        self.terrain_np = render.attach_new_node(self.terrain_bullet_node)
        self.terrain_np.set_collide_mask(BitMask32.bit(0))
        self.world.attach(self.terrain_np.node())


    def start_game(self):
        self.notice_text_obj.hide()

        self.player = Humanoid(self.world, self.terrain_bullet_node, 0, 0, debug=debug.getboolean("debug-joints"))

        self.gui = DefaultGUI(text_input_func=self.player_say)

        base.camera.reparent_to(self.player.lower_torso)

        cam_control = CameraControl(camera, base.mouseWatcherNode)
        cam_control.attach_to(self.player.lower_torso)

        taskMgr.add(cam_control.move_camera, "MoveCameraTask")

        base.accept("wheel_down", cam_control.wheel_down)
        base.accept("wheel_up", cam_control.wheel_up)

        setup_controls(self.player.get_body())

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")


    def player_say(self, text):
        if not text:
            self.gui.focus_out_text_field()
            return
        self.gui.input_field.clear_text()
        logger.debug(f"The player said: {text}")
        self.player.say(text)
        you_say = f"You say: \"{text}\""
        self.nlp_manager.new_speech_task(self.npc1, you_say)
        self.gui.focus_out_text_field()


    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.get_dt()

        self.world.do_physics(dt, 5, 1.0 / 80.0)

        # Define controls
        if self.gui.input_field.is_focused():
            interpret_controls(self.player, stand_still=True)
        else:
            interpret_controls(self.player)

#        data = self.player.get_compressed_state()
#        uncompressed = struct.unpack(self.player.get_state_format(), data)
#        self.npc1.set_state_shifted(*uncompressed, 2, 0)
        self.npc1.stand_still()
        self.nlp_manager.update()

        return task.cont


Game()
