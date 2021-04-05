import struct
from time import sleep

from direct.gui.DirectGui import DirectFrame, DirectEntry, DirectButton
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
from src.default_gui import DefaultGUI
from src.getconfig import debug
from src.humanoid import Humanoid
from src.utils import create_or_load_walk_map, create_and_texture_terrain


class Game:
    def __init__(self):
        # Increase camera FOV as well as the far plane
        base.camLens.set_fov(90)
        base.camLens.set_near_far(0.1, 50000)
        self.ip_addr = ""
        self.port = "5005"

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

        self.terrain_init_thread = threading.Thread(target=self.initialize_terrain, args=())
        self.terrain_init_thread.start()

        self.connect_dialog = DirectFrame(frameColor=(0, 0, 0, 0.8),
                                     frameSize=(-0.7, 0.7, -0.3, 0.3),
                                     pos=(0, -1, 0))
        scale = 0.05
        self.ip_field = DirectEntry(scale=scale, command=self.focus_in_port, parent=self.connect_dialog,
                                    text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0.3), width=12,
                                    pos=(-0.2, 0, 0.04),
                                    initialText="", numLines=1, focus=1)

        self.port_field = DirectEntry(scale=scale, command=self.focus_in_connect, parent=self.connect_dialog,
                                      text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0.3), width=3,
                                      pos=(-0.2, 0, -0.04),
                                      initialText="5005", numLines=1, focus=0)

        self.notice_text_obj = OnscreenText(text="Enter the IP address of the other player", style=1, fg=(1, 1, 1, 1), scale=.05,
                                            shadow=(0, 0, 0, 1), parent=self.connect_dialog,
                                            pos=(0.0, 0.2), align=TextNode.ACenter)
        self.notice_text_obj.setBin("frontBin", 1)

        self.ip_question = OnscreenText(text="IP:", style=1, fg=(1, 1, 1, 1), scale=scale,
                                        shadow=(0, 0, 0, 1), parent=self.connect_dialog,
                                        pos=(-0.4, 0.04), align=TextNode.ACenter)
        self.ip_question.setBin("frontBin", 1)

        self.port_question = OnscreenText(text="Port:", style=1, fg=(1, 1, 1, 1), scale=scale,
                                          shadow=(0, 0, 0, 1), parent=self.connect_dialog,
                                          pos=(-0.4, -0.04), align=TextNode.ACenter)
        self.port_question.setBin("frontBin", 1)

        DirectButton(text="Quit",
                     scale=scale, command=exit, parent=self.connect_dialog,
                     pos=(-0.2, 0, -0.2))

        self.connect_button = DirectButton(text="Connect",
                                           scale=scale, command=self.set_ip_addr, parent=self.connect_dialog,
                                           pos=(0.2, 0, -0.2))

        taskMgr.add(self.wait_for_connection, "pvp-init")


    def focus_in_port(self, ignore_me):
        self.ip_field['focus'] = False
        self.port_field['focus'] = True


    def focus_in_connect(self, ignore_me):
        # IMPLEMENT ME
        self.set_ip_addr()


    def wait_for_connection(self, task):
        while not self.ip_addr:
            return task.cont
        while not self.port:
            return task.cont

        self.connect_dialog.destroy()
        self.terrain_init_thread.join()
        self.start_game()


    def set_ip_addr(self):
        self.ip_addr = self.ip_field.get()
        self.port = self.port_field.get()

        if not self.ip_addr:
            self.ip_field['focus'] = True
            self.port_field['focus'] = False
            return
        if not self.port:
            self.ip_field['focus'] = False
            self.port_field['focus'] = True


    def initialize_terrain(self):
        # Set a heightfield, the heightfield should be a 16-bit png and
        # have a quadratic size of a power of two.
        elevation_img = PNMImage(Filename("worldmaps/seed_16783_grayscale.png"))
        texture_img = PNMImage(Filename("worldmaps/seed_16783_satellite.png"))
        create_and_texture_terrain(elevation_img, self.terrain_height, texture_img)

        # Collision detection for the terrain
        terrain_colshape = BulletHeightfieldShape(
            create_or_load_walk_map("worldmaps/seed_16783_grayscale.png", "worldmaps/seed_16783_ocean.png"),
            self.terrain_height, ZUp)
        terrain_colshape.set_use_diamond_subdivision(True)

        self.terrain_bullet_node.add_shape(terrain_colshape)
        self.terrain_np = render.attach_new_node(self.terrain_bullet_node)
        self.terrain_np.set_collide_mask(BitMask32.bit(0))
        self.world.attach(self.terrain_np.node())


    def start_game(self):
        self.player = Humanoid(self.world, self.terrain_bullet_node, 0, 0, debug=debug.getboolean("debug-joints"))

        self.gui = DefaultGUI(text_input_func=self.player_say)

        base.camera.reparent_to(self.player.lower_torso)

        cam_control = CameraControl(camera, base.mouseWatcherNode)
        cam_control.attach_to(self.player.lower_torso)

        taskMgr.add(cam_control.move_camera, "MoveCameraTask")

        base.accept("wheel_down", cam_control.wheel_down)
        base.accept("wheel_up", cam_control.wheel_up)

        setup_controls()

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")


    def player_say(self, text):
        self.gui.text_field.enterText('Disabled for multiplayer')
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

        data = self.player.get_compressed_state()
        uncompressed = struct.unpack(self.player.get_state_format(), data)

        return task.cont


Game()
