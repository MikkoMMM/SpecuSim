from direct.gui.DirectGui import *
from src.gui.inputfield import InputField
from panda3d.core import *


def ignore_enter():
    base.ignore("enter")


class DefaultGUI:
    def __init__(self, enable_text_field=True, text_input_func=print):
        bar_start = -0.8

        self.screen_frame = DirectFrame(state=DGG.NORMAL, frameColor=(1, 0, 0, 0.0), frameSize=(-9, 9, -9, 9))

        gui_bar = DirectFrame(frameColor=(0, 0, 0, 0.8),
                              frameSize=(-9, 9, -1, bar_start),
                              pos=(0, -1, 0))
        # Each width unit seems to be a 2/scale'th of a screen on a rectangular aspect ratio
        scale = 0.05
        if enable_text_field:
            # For the input fields.
            # It is necessary to set up a hilite text property for selected text color

            props_mgr = TextPropertiesManager.get_global_ptr()
            col_prop = TextProperties()
            col_prop.set_text_color((0.5, 0.5, 1., 1.))
            props_mgr.set_properties("hilite", col_prop)

            self.input_field = InputField((-15 * scale, 0, (bar_start - 0.95) / 2), scale, 30, on_commit=(text_input_func, ()),
                                          parent=gui_bar, text_fg=(1, 1, 1, 1), normal_bg=(0, 0, 0, 0.3), hilite_bg=(0.3, 0.3, 0.3, 0.3),
                                          num_lines=3, initial_text="Press Enter to start talking", clear_initial=True,
                                          focus_in_cmd=ignore_enter)

            base.accept("enter", self.input_field.focus)
            self.screen_frame.bind(DGG.B1PRESS, self.focus_out_text_field)
            self.screen_frame.bind(DGG.B2PRESS, self.focus_out_text_field)
            self.screen_frame.bind(DGG.B3PRESS, self.focus_out_text_field)


    def focus_out_text_field(self, event=None):
        self.input_field.unfocus()
        # If we don't delay, it will just focus back in again right then and there.
        taskMgr.doMethodLater(globalClock.get_dt()*2, base.accept, 'Set enter', extraArgs=["enter", self.input_field.focus])
