from direct.stdpy import threading
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletWorld
from panda3d.bullet import ZUp
from panda3d.core import BitMask32
from panda3d.core import PNMImage, Filename
from panda3d.core import Vec3
from panda3d.core import Shader

from src.camera import CameraControl
from src.default_controls import setup_controls, interpret_controls
from src.gui.default_gui import DefaultGUI
from src.getconfig import logger, debug
from src.humanoid import Humanoid
from src.utils import create_and_texture_terrain, create_or_load_walk_map


class Game:
    def __init__(self):
        self.doppelganger_num = 0  # Actual number will be doppelganger_num^2-1 if odd and doppelganger_num^2 if even

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

        self.terrain_init_thread = threading.Thread(target=self.initialize_terrain, args=())
        self.terrain_init_thread.start()

        # Characters must be created only after the terrain_bullet_node has been finalized
        self.terrain_init_thread.join()
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

        base.camera.reparent_to(self.player.lower_torso)

        cam_control = CameraControl(camera, base.mouseWatcherNode)
        cam_control.attach_to(self.player.lower_torso)

        taskMgr.add(cam_control.move_camera, "MoveCameraTask")

        base.accept("wheel_down", cam_control.wheel_down)
        base.accept("wheel_up", cam_control.wheel_up)
        base.accept('f1', base.toggle_wireframe)
        base.accept('f2', base.toggle_texture)

        setup_controls(self.player.get_body())

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")


    def initialize_terrain(self):
        # This is what we came here to do, right? Visual debugging stuff.
        self.world_np = render.attach_new_node('World')
        self.debug_np = self.world_np.attach_new_node(BulletDebugNode('Debug'))
        self.debug_np.node().show_normals(True)
        self.debug_np.node().show_bounding_boxes(False)
        self.debug_np.node().show_constraints(True)
        self.debug_np.show()
        self.world.set_debug_node(self.debug_np.node())

        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        elevation_img = PNMImage(Filename("worldmaps/debug_heightmap.png"))
        texture_img = PNMImage(Filename("worldmaps/seed_16783_satellite.png"))
        create_and_texture_terrain(elevation_img, self.terrain_height, texture_img)

        # Collision detection for the terrain. Preferably the image should have a size 1 pixel taller and wider than elevation_img.
        terrain_colshape = BulletHeightfieldShape(
            create_or_load_walk_map("worldmaps/debug_heightmap.png", "worldmaps/debug_ocean.png"),
            self.terrain_height, ZUp)
        terrain_colshape.set_use_diamond_subdivision(True)

        self.terrain_bullet_node.add_shape(terrain_colshape)
        self.terrain_np = render.attach_new_node(self.terrain_bullet_node)
        self.terrain_np.set_collide_mask(BitMask32.bit(0))
        self.world.attach(self.terrain_np.node())


    def player_say(self, text):
        if not text:
            self.gui.focus_out_text_field()
            return
        self.gui.input_field.clear_text()
        logger.debug(f"The player said: {text}")
        self.player.say(text)
        self.gui.focus_out_text_field()


    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.get_dt()

        self.world.do_physics(dt, 5, 1.0 / 80.0)

        # Define controls
        if self.gui.input_field.is_focused():
            interpret_controls(self.player, stand_still=True)
            for doppelganger in self.doppelgangers:
                interpret_controls(doppelganger, stand_still=True)
        else:
            interpret_controls(self.player)
            for doppelganger in self.doppelgangers:
                interpret_controls(doppelganger)

        return task.cont


Game()
