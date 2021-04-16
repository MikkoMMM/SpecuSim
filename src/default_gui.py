from direct.gui.DirectGui import DirectFrame
from src.inputfield import InputField


class DefaultGUI:
    def __init__(self, enable_text_field=True, text_input_func=print):
        wx = base.win.get_x_size()
        wy = base.win.get_y_size()
        bar_start = -0.8
        gui_bar = DirectFrame(frameColor=(0, 0, 0, 0.8),
                              frameSize=(-wx / 2, wx / 2, -1, bar_start),
                              pos=(0, -1, 0))
        # Each width unit seems to be a 2/scale'th of a screen on a rectangular aspect ratio
        scale = 0.05
        if enable_text_field:
            self.input_field = InputField((-15 * scale, 0, (bar_start - 0.95) / 2), scale, 30, on_commit=(text_input_func, ()),
                                          parent=gui_bar, text_fg=(1, 1, 1, 1), normal_bg=(0, 0, 0, 0.3), hilite_bg=(0.3, 0.3, 0.3, 0.3),
                                          num_lines=3, initial_text="Press Enter to start talking")

            # For whatever reason, we seem to need a delay, in some circumstances at least
            taskMgr.doMethodLater(globalClock.get_dt(), base.accept, 'Set enter', extraArgs=["enter", self.focus_in_text_field_initial])


    def focus_in_text_field_initial(self):
        self.input_field.clear_text()
        self.focus_in_text_field()


    def focus_in_text_field(self):
        self.input_field.focus()
        base.ignore("enter")


    def focus_out_text_field(self):
        self.input_field.unfocus()
        # If we don't delay, it will just focus back in again right then and there.
        taskMgr.doMethodLater(globalClock.get_dt()*2, base.accept, 'Set enter', extraArgs=["enter", self.focus_in_text_field])
