from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import get_bullet_version
from panda3d.core import PNMImage, Filename
from panda3d.core import load_prc_file_data, PStatClient

from src.getconfig import logger, settings, debug
from src.menu import Menu


class MyApp(ShowBase):
    def __init__(self):
        # Load some configuration variables, its important for this to happen
        # before the ShowBase is initialized
        load_prc_file_data("", """
            window-title SpecuSim - An Early Prototype

            # For shader compatibility with Intel graphics we are going to force a higher OpenGL version than it might report
            # It requests a forward-compatible context, but disables the use of the compatibility profile,
            # so requires the use of custom shaders
            gl-version 3 2

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

        if debug.getint("log-level") <= 10:
            load_prc_file_data("", "gl-debug 1")

        # Initialize the showbase
        ShowBase.__init__(self)
        # In case window size would be at first detected incorrectly, buy a bit of time.
        base.graphicsEngine.render_frame()

        self.physics_debug = False
        self.doppelganger_num = 0  # Actual number will be doppelganger_num^2-1 if odd and doppelganger_num^2 if even

        logger.debug(f"Using Bullet Physics version {get_bullet_version()}")

        if debug.getboolean("enable-pstats"):
            load_prc_file_data("", "task-timer-verbose 1")
            load_prc_file_data("", "pstats-tasks 1")
            PStatClient.connect()

        if settings.getboolean("enable-fps-meter"):
            base.set_frame_rate_meter(True)

        self.menu_img = PNMImage(Filename("textures/menu.jpg"))

        self.main_menu = Menu(self.menu_img, aspect_ratio_keeping_scale=1, destroy_afterwards=True)
        self.main_menu.change_button_style(PNMImage(Filename("textures/empty_button_52.png")), aspect_ratio_keeping_scale=2)
        self.main_menu.change_select_style(PNMImage(Filename("textures/select.png")), aspect_ratio_keeping_scale=2)
        self.main_menu.add_button("Main Game", self.main_game, y=-0.1)
        self.main_menu.add_button("PvP Duel", self.pvp, y=0)
        self.main_menu.add_button("Debug Mode", self.debug_mode, y=0.1)
        self.main_menu.add_button("Exit Game", exit, y=0.2)
        self.main_menu.show_menu()


    def debug_mode(self):
        # noinspection PyUnresolvedReferences
        import game_modes.debug_mode.init


    def pvp(self):
        # noinspection PyUnresolvedReferences
        import game_modes.pvp.init


    def main_game(self):
        # noinspection PyUnresolvedReferences
        import game_modes.main.init


app = MyApp()
app.run()
