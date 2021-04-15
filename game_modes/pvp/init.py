import struct
import socket
from time import sleep, time

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
from panda3d.core import Vec3, CullBinManager, TextPropertiesManager, TextProperties

from src.camera import CameraControl
from src.default_controls import setup_controls, interpret_controls
from src.default_gui import DefaultGUI
from src.getconfig import debug, logger
from src.humanoid import Humanoid
from src.utils import create_or_load_walk_map, create_and_texture_terrain, paste_into, is_focused
from src.inputfield import InputField


class Game:
    ip_lock = threading.Lock()  # Just in case


    def __init__(self):
        # Increase camera FOV as well as the far plane
        base.camLens.set_fov(90)
        base.camLens.set_near_far(0.1, 50000)
        self.ip_addr = ""
        self.port = 5005
        self.lag = 0

        # For the input fields.
        # It is necessary to set up a hilite text property for selected text color

        props_mgr = TextPropertiesManager.get_global_ptr()
        col_prop = TextProperties()
        col_prop.set_text_color((1., 1., 1., 1.))
        props_mgr.set_properties("hilite", col_prop)

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
                                     frameSize=(-0.8, 0.8, -0.3, 0.3),
                                     pos=(0, -1, 0))
        scale = 0.05
        self.ip_field = InputField((-0.4, 0, 0.04), scale, 22, on_commit=(self.focus_in_port, ()), parent=self.connect_dialog,
                                   text_fg=(1, 1, 1, 1), normal_bg=(0, 0, 0, 0.3), hilite_bg=(0.3, 0.3, 0.3, 0.3))
        self.ip_field.focus()
        self.port_field = InputField((-0.4, 0, -0.04), scale, 4, on_commit=(self.focus_in_connect, ()), parent=self.connect_dialog,
                                     text_fg=(1, 1, 1, 1), normal_bg=(0, 0, 0, 0.3), hilite_bg=(0.3, 0.3, 0.3, 0.3),
                                     initial_text="5005")

        self.notice_text_obj = OnscreenText(text="Enter the IPv4 address of the other player", style=1, fg=(1, 1, 1, 1), scale=.05,
                                            shadow=(0, 0, 0, 1), parent=self.connect_dialog, pos=(0.0, 0.2), align=TextNode.ACenter)

        self.ip_question = OnscreenText(text="IP:", style=1, fg=(1, 1, 1, 1), scale=scale,
                                        shadow=(0, 0, 0, 1), parent=self.connect_dialog, pos=(-0.6, 0.04), align=TextNode.ACenter)

        self.port_question = OnscreenText(text="Port:", style=1, fg=(1, 1, 1, 1), scale=scale,
                                          shadow=(0, 0, 0, 1), parent=self.connect_dialog, pos=(-0.6, -0.04), align=TextNode.ACenter)

        DirectButton(text="Quit",
                     scale=scale, command=exit, parent=self.connect_dialog,
                     pos=(-0.2, 0, -0.2))

        self.connect_button = DirectButton(text="Connect",
                                           scale=scale, command=self.set_ip_addr, parent=self.connect_dialog,
                                           pos=(0.2, 0, -0.2))

        self.lag_meter = OnscreenText(text="", style=1, fg=(1, 1, 1, 1), scale=.05,
                                            shadow=(0, 0, 0, 1), pos=(-1.0, 0.9), align=TextNode.ACenter)
        self.lag_meter.setBin("frontBin", 1)

        self.sock = socket.socket(socket.AF_INET,  # Internet
                                  socket.SOCK_DGRAM)  # UDP
        self.sock.bind(("", self.port))
        self.sock.setblocking(False)
        taskMgr.add(self.wait_connection_info, "pvp-init")

        # Characters must be created only after the terrain_bullet_node has been finalized
        self.terrain_init_thread.join()
        self.player = Humanoid(self.world, self.terrain_bullet_node, 0, 0, debug=debug.getboolean("debug-joints"))
        self.opponent = Humanoid(self.world, self.terrain_bullet_node, 2, 0, debug=debug.getboolean("debug-joints"))
        self.player_start_time = time() % 10
        self.opponent_start_time = -1
        self.network_listen_thread = threading.Thread(target=self.network_listen_initial, args=())
        self.network_listen_thread.start()


    def network_listen_initial(self):
        while True:
            with self.ip_lock:
                try:
                    data, addr = self.sock.recvfrom(100)  # buffer size
                    uncompressed = struct.unpack(self.packet_format(), data)
                    self.opponent_start_time = uncompressed[0]
                    self.opponent_new_state = uncompressed[1:]
                    if self.ip_addr:
                        return
                    if addr:
                        self.ip_addr = addr[0]
                        logger.debug(f"Connection from {self.ip_addr}")
                        return
                except socket.error as e:
                    pass
            sleep(0.05)


    def packet_format(self):
        return f"f{self.player.get_state_format()}"


    def focus_in_port(self, ignore_me):
        self.port_field.focus()


    def focus_in_connect(self, ignore_me):
        # TODO: IMPLEMENT ME
        self.set_ip_addr()


    def wait_connection_info(self, task):
        if not self.ip_addr:
            return task.cont
        if not self.port:
            return task.cont
        game_state_packet = struct.pack("f", self.player_start_time) + self.player.get_compressed_state()
        self.sock.sendto(game_state_packet, (self.ip_addr, self.port))

        if self.opponent_start_time < 0:
            return task.cont

        base.ignore("control-v")
        base.ignore("shift-insert")

        if self.opponent_start_time < self.player_start_time:
            body = self.player.get_body()
            body.set_x(20)
            body.set_y(20)
            self.opponent.set_state_shifted(*self.opponent_new_state, -20, -20)
        else:
            body = self.player.get_body()
            body.set_x(-20)
            body.set_y(-20)
            self.opponent.set_state_shifted(*self.opponent_new_state, 20, 20)

        self.network_listen_thread.join()
        self.sock.setblocking(True)
        self.ip_field.destroy()
        self.port_field.destroy()
        self.connect_dialog.destroy()
        self.network_listen_thread = threading.Thread(target=self.network_listen, args=())
        self.network_listen_thread.start()

        self.start_game()
        return task.done


    def set_ip_addr(self):
        with self.ip_lock:
            self.ip_addr = self.ip_field.get()

            if not self.ip_addr:
                self.ip_field.focus()
                return
        self.port = int(self.port_field.get())
        if not self.port:
            self.port_field.focus()


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
        self.gui = DefaultGUI(enable_text_field=False)  # Chat is currently not implemented, due to various concerns

        base.camera.reparent_to(self.player.lower_torso)

        cam_control = CameraControl(camera, base.mouseWatcherNode)
        cam_control.attach_to(self.player.lower_torso)

        taskMgr.add(cam_control.move_camera, "MoveCameraTask")

        base.accept("wheel_down", cam_control.wheel_down)
        base.accept("wheel_up", cam_control.wheel_up)

        setup_controls()

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")


    def network_listen(self):
        while True:
            game_state_packet = self.sock.recv(100)  # buffer size
            uncompressed = struct.unpack(self.packet_format(), game_state_packet)
            opponent_time = uncompressed[0]
            cur_time = time() % 10
            if opponent_time > cur_time:
                self.lag = cur_time + 10 - opponent_time
            else:
                self.lag = cur_time - opponent_time
            self.opponent_new_state = uncompressed[1:]


    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        self.lag_meter.setText(f"Lag: {str(round(self.lag*1000))} ms")
        dt = globalClock.get_dt()

        self.world.do_physics(dt, 5, 1.0 / 80.0)

        # Define controls
        interpret_controls(self.player)
        self.opponent.stand_still()
        self.opponent.set_state(*self.opponent_new_state)

        game_state_packet = struct.pack("f", time() % 10) + self.player.get_compressed_state()
        self.sock.sendto(game_state_packet, (self.ip_addr, self.port))
        return task.cont


Game()
