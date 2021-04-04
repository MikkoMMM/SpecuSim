from direct.gui.DirectGui import DirectFrame, DirectEntry


class DefaultGUI:
    def __init__(self, text_input_func):
        wx = base.win.get_x_size()
        wy = base.win.get_y_size()
        bar_start = -0.8
        gui_bar = DirectFrame(frameColor=(0, 0, 0, 0.8),
                              frameSize=(-wx / 2, wx / 2, -1, bar_start),
                              pos=(0, -1, 0))
        # Each width unit seems to be a 2/scale'th of a screen on a rectangular aspect ratio
        scale = 0.05
        self.text_field = DirectEntry(text="", scale=scale, command=text_input_func, parent=gui_bar,
                                      text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0.3), width=30,
                                      pos=(-15 * scale, 0, (bar_start - 0.95) / 2),
                                      initialText="Press Enter to start talking", numLines=3, focus=0,
                                      focusInCommand=self.focus_in_text_field_initial)

        # For whatever reason, we seem to need a delay, in some circumstances at least
        taskMgr.doMethodLater(globalClock.get_dt(), base.accept, 'Set enter', extraArgs=["enter", self.focus_in_text_field_initial])


    def focus_in_text_field_initial(self):
        self.text_field.enterText('')
        self.focus_in_text_field()


    def focus_in_text_field(self):
        self.text_field['focus'] = True
        base.ignore("enter")


    def focus_out_text_field(self):
        self.text_field['focus'] = False
        # If we don't delay, it will just focus back in again right then and there.
        taskMgr.doMethodLater(globalClock.get_dt(), base.accept, 'Set enter', extraArgs=["enter", self.focus_in_text_field])
