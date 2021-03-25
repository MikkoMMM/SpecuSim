import os
from math import sqrt, atan2, degrees, acos, pi, radians
from pathlib import Path
from time import sleep

from direct.gui.DirectGui import DirectFrame, DirectEntry
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.InputStateGlobal import inputState
from direct.showbase.ShowBase import ShowBase
from direct.stdpy import thread
from direct.task import Task
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletHeightfieldShape
from panda3d.bullet import BulletRigidBodyNode
# from direct.task import Task
from panda3d.bullet import BulletWorld
from panda3d.bullet import ZUp
from panda3d.bullet import get_bullet_version
from panda3d.core import BitMask32
from panda3d.core import PNMImage, Filename
from panda3d.core import SamplerState, TextNode
from panda3d.core import Vec3, load_prc_file_data, PStatClient, CullBinManager, Vec2

from src.language_processing.nlp_manager import NLPManager
from src.camera import CameraControl
from src.humanoid import Humanoid
from src.language_processing.getconfig import settings
from src.language_processing.gpt2generator import GPT2Generator
from src.menu import Menu
from src.utils import create_or_load_walk_map, create_shader_terrain_mesh
import random

from multiprocessing import Pool

# from src.weapons.sword import Sword


def timediff(time1, time2):
    return time1 - time2


# Function to put instructions on the screen.
def add_instructions(pos, msg, z_bin=None):
    text_object = OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), scale=.05,
                               shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                               pos=(0.08, -pos - 0.04), align=TextNode.ALeft)
    if z_bin:
        text_object.setBin(z_bin, 1)

    return text_object


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

        self.gui = True  # A toggle for the GUI for testing puposes
        self.performance_analysis = True  # Enable pstat support and show frame rate
        self.physics_debug = False  # Show wireframes for the physics objects.
        self.nlp_debug = True  # Stuff that makes debugging natural language processing faster
        self.debug_messages = True  # Some extraneous information
        self.doppelganger_num = 4  # Actual number will be doppelganger_num^2-1 if odd and doppelganger_num^2 if even

        if self.debug_messages:
            print("Using Bullet Physics version ", get_bullet_version())
            print()

        if self.performance_analysis:
            load_prc_file_data("", "task-timer-verbose 1")
            load_prc_file_data("", "pstats-tasks 1")

            base.set_frame_rate_meter(True)
            PStatClient.connect()

        self.terrain_loaded = False
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

        self.dxdy_to_angle = [[radians(45), radians(90), radians(135)], [radians(0), -999, radians(180)], [radians(-45), radians(-90),
                                                                                                           radians(-135)]]

        # Heightfield's height
        self.terrain_height = 25.0

        # Physics setup
        self.world = BulletWorld()
        # The custom ground collision doesn't go well along with gravity, but some aesthetics depend on it.
        self.world.set_gravity(Vec3(0, 0, -9.81))

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

        thread.start_new_thread(self.initialize_terrain, args=())


    def start_without_nlp(self):
        self.start_game()


    def start_with_nlp(self):
        self.main_menu.hide_menu()

        model_dir = "language_models"
        models = [x for x in Path(model_dir).iterdir() if x.is_dir()]
        failed_env_load = False
        while True:
            try:
                transformers_pretrained = os.environ.get("TRANSFORMERS_PRETRAINED_MODEL", False)
                if transformers_pretrained and not failed_env_load:
                    # Keep it as a string, so that transformers library will load the generic model
                    model = transformers_pretrained
                    assert isinstance(model, str)
                else:
                    # Convert to path, so that transformers library will load the model from our folder
                    if not models:
                        raise FileNotFoundError(
                            'There are no models in the models directory! You must download a pytorch compatible model!')
                    if os.environ.get("MODEL_FOLDER", False) and not failed_env_load:
                        model = Path(model_dir + os.environ.get("MODEL_FOLDER", False))
                    elif len(models) > 1:
                        self.notice_text_obj.text = "You have multiple models in your models folder. Please select one to load:"

                        menu = Menu(self.menu_img, aspect_ratio_keeping_scale=1, hide_afterwards=True)
                        menu.change_button_style(PNMImage(Filename("textures/empty_button_52.png")), aspect_ratio_keeping_scale=2)
                        menu.change_select_style(PNMImage(Filename("textures/select.png")), aspect_ratio_keeping_scale=2)

                        for i in range(len(models)):
                            menu.add_button(models[i].name, self.nlp_model_chosen, args=[models[i]], y=-0.1 + 0.1 * i)
                        menu.add_button("(Exit)", exit, y=0.5)
                        menu.show_menu()
                        return
                    else:
                        model = models[0]
                        print("Using model: " + str(model))
                    assert isinstance(model, Path)
                self.nlp_model_chosen(model)
                break
            except OSError:
                if len(models) == 0:
                    self.notice_text_obj.text = "You do not seem to have any models installed. Place a model in the '" + model_dir + "' subfolder"
                    base.graphicsEngine.render_frame()
                    # Scan for models again
                    models = [x for x in Path(model_dir).iterdir() if x.is_dir()]
                else:
                    failed_env_load = True
                    self.notice_text_obj.text = "Model could not be loaded. Please try another model."
                continue
            except KeyboardInterrupt:
                print("Model load cancelled. ")
                exit(0)


    def nlp_model_chosen(self, model):
        self.notice_text_obj.text = "Loading language model. This may take a few minutes."

        assert isinstance(model, Path)
        thread.start_new_thread(self.load_generator, args=(), kwargs={
            "model_path": model,
            "generate_num": settings.getint("generate-num"),
            "temperature": settings.getfloat("temp"),
            "top_k": settings.getint("top-keks"),
            "top_p": settings.getfloat("top-p"),
            "repetition_penalty": settings.getfloat("rep-pen")})

        while not hasattr(self, 'generator'):
            base.graphicsEngine.render_frame()
            sleep(0.05)

        while not self.terrain_loaded:
            self.notice_text_obj.text = "Loading terrain."
            base.graphicsEngine.render_frame()
            sleep(0.05)

        self.npc1 = Humanoid(self.world, self.terrain_bullet_node, -2, 2)

        self.nlp_manager = NLPManager(self.generator, self.nlp_debug)
#        self.nlp_manager.new_speech_task(self.npc1, "'Ello, 'ello, 'ello!")

#        thread.start_new_thread(nlp_manager.act, args=(self.generator, "You are speaking to a man.", "You say to him: \"Hello!\""),
        #        kwargs={
#            "output": self.npc1.speech_field, "debug": self.nlp_debug})

        self.start_game()


    def load_generator(self, **kwargs):
        self.generator = GPT2Generator(**kwargs)


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
        self.terrain_loaded = True

        return Task.done


    def start_game(self):
        self.main_menu.hide_menu()

        self.notice_text_obj.text = "Loading terrain"
        while not self.terrain_loaded:
            base.graphicsEngine.render_frame()
            sleep(0.01)
        self.notice_text_obj.hide()

        self.inst1 = add_instructions(0.06, "[WASD]: Move")
        self.inst2 = add_instructions(0.12, "[QE]: Rotate")
        self.inst2 = add_instructions(0.18, "[+-]: Change speed")
        self.inst3 = add_instructions(0.24, "Middle mouse button: Rotate camera")
        self.inst4 = add_instructions(0.30, "Right mouse button: Adjust zoom")
        self.inst5 = add_instructions(0.36, "")
        self.inst6 = add_instructions(0.42, "")
        # inst7 is reserved for NLP stuff

        self.player = Humanoid(self.world, self.terrain_bullet_node, 0, 0, debug=self.physics_debug,
                               debug_text_node=self.inst6)

        self.doppelgangers = []
        for i in range(self.doppelganger_num):
            for j in range(self.doppelganger_num):
                if i == (self.doppelganger_num - 1) / 2 and j == (self.doppelganger_num - 1) / 2:
                    continue
                self.doppelgangers.append(
                    Humanoid(self.world, self.terrain_bullet_node, i*2 - (self.doppelganger_num - 1),
                             j*2 - (self.doppelganger_num - 1)))

        if self.gui:
            wx = base.win.get_x_size()
            wy = base.win.get_y_size()
            bar_start = -0.8
            gui_bar = DirectFrame(frameColor=(0, 0, 0, 1),
                                  frameSize=(-wx / 2, wx / 2, -1, bar_start),
                                  pos=(0, -1, 0))
            # Each width unit seems to be a 2/scale'th of a screen on a rectangular aspect ratio
            scale = 0.05
            self.text_field = DirectEntry(text="", scale=scale, command=self.player_say, parent=gui_bar,
                                          text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 1), width=30,
                                          pos=(-15 * scale, 0, (bar_start - 1) / 2), suppressKeys=1,
                                          initialText="Press Enter to start talking", numLines=2, focus=0,
                                          focusOutCommand=self.focus_out_text_field)

        self.camera.reparent_to(self.player.lower_torso)

        cam_control = CameraControl(camera, self.mouseWatcherNode)
        cam_control.attach_to(self.player.lower_torso)

        self.taskMgr.add(cam_control.move_camera, "MoveCameraTask")

        self.accept("wheel_down", cam_control.wheel_down)
        self.accept("wheel_up", cam_control.wheel_up)

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
        self.accept_once("enter", self.focus_in_text_field_initial)

        # Tasks that are repeated ad infinitum
        taskMgr.add(self.update, "update")
        if self.debug_messages:
            render.analyze()


#    def act(self, num):
#        nlp_manager.act(self.generator, "You are speaking to a man.", "You say to him: \"Hello!\"", output=self.doppelgangers[
#            num].speech_field, debug=self.nlp_debug)


    def focus_in_text_field_initial(self):
        self.text_field.enterText('')
        self.focus_in_text_field()


    def player_say(self, text):
        self.text_field.enterText('')
        self.player.say(text)
        if hasattr(self, 'nlp_manager'):
            for doppelganger in random.sample(self.doppelgangers, len(self.doppelgangers)):
                self.nlp_manager.new_speech_task(doppelganger, text)
        self.focus_out_text_field()


    def focus_in_text_field(self):
        self.text_field['focus'] = True


    def focus_out_text_field(self):
        self.text_field['focus'] = False
        self.accept("enter", self.focus_in_text_field)


    # Everything that needs to be done every frame goes here.
    # Physics updates and movement and stuff.
    def update(self, task):
        dt = globalClock.get_dt()

        self.world.do_physics(dt, 5, 1.0 / 80.0)

        # Define controls
        dx = dy = 1
        if inputState.is_set('forward'):
            dy -= 1
        if inputState.is_set('backward'):
            dy += 1
        if inputState.is_set('left'):
            dx -= 1
        if inputState.is_set('right'):
            dx += 1
        direction = self.dxdy_to_angle[dy][dx]

        if direction > -900:
            self.player.walk_in_dir(direction)
            for doppelganger in self.doppelgangers:
                doppelganger.walk_in_dir(direction)
        else:
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

        self.inst5.text = "Speed " + str(round(sqrt(
            pow(self.player.lower_torso.node().get_linear_velocity()[0], 2) + pow(
                self.player.lower_torso.node().get_linear_velocity()[1], 2)), 2)) + " / " + str(
            round(self.player.walk_speed, 1)) + " m/s"

        if hasattr(self, 'npc1'):
            self.npc1.stand_still()

        #        self.player.setRightHandHpr(self.heading, self.pitch, self.roll)

        return task.cont


app = MyApp()
app.run()
