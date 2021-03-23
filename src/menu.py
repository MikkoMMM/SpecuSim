# Credit: RenderPipeline contributors

from sys import exit

from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectGuiBase import DGG
from direct.gui.DirectLabel import DirectLabel
from direct.interval.LerpInterval import LerpColorScaleInterval
from direct.interval.MetaInterval import Sequence
from panda3d.core import TextNode, PNMImage, Filename, Texture


class Menu:
    def __init__(self, menu_tex_img, aspect_ratio_keeping_scale=None, use_keyboard=True, auto_hide=False, **keywords):
        self.use_keyboard = use_keyboard
        self.auto_hide = auto_hide

        kx = menu_tex_img.get_x_size()
        ky = menu_tex_img.get_y_size()
        menu_tex = Texture("menu texture")
        menu_tex.load(menu_tex_img)

        if aspect_ratio_keeping_scale:
            scale = aspect_ratio_keeping_scale
            wx = kx / ky

            self.menu_frame = DirectFrame(frameSize=(-scale * wx, scale * wx, -scale, scale), **keywords)
        else:
            self.menu_frame = DirectFrame(**keywords)

        self.menu_frame["frameTexture"] = menu_tex
        self.menu_frame.reparent_to(base.aspect2d)
        self.menu_frame.set_transparency(True)
        self.menu_frame.hide()

        self.entries = []
        self.funcs = []
        self.args = []

        self.button_tex = Texture("button texture")
        self.button_vert_aspect_r = 1
        self.button_scale = 1

        self.button_style = {
            "frameColor": (1, 1, 1, 1),
            "relief": DGG.FLAT,
            "rolloverSound": None,
            "clickSound": None,
            "parent": self.menu_frame,
            "scale": 0.1,
        }

        self.text_style = {
            "text_fg": (0.2, 0.2, 0.2, 1),
            "relief": None,
            "text_align": TextNode.ACenter,
            "text_scale": 0.5,
        }

        self.active_entry = 0
        self.select_frame = DirectFrame()
        self.select_frame.hide()


    def set_button_texture(self, image):
        kx = image.get_x_size()
        ky = image.get_y_size()
        self.button_vert_aspect_r = ky / kx
        self.button_tex.load(image)


    def change_button_style(self, img=None, aspect_ratio_keeping_scale=None, **keywords):
        if img:
            self.set_button_texture(img)
        self.button_scale = aspect_ratio_keeping_scale
        for kw in keywords:
            self.button_style[kw] = keywords[kw]


    def change_text_style(self, **keywords):
        for kw in keywords:
            self.text_style[kw] = keywords[kw]


    def change_select_style(self, img, aspect_ratio_keeping_scale=None, **keywords):
        kx = img.get_x_size()
        ky = img.get_y_size()
        vert_aspect_r = ky / kx
        tex = Texture("select frame texture")
        tex.load(img)

        for kw in keywords:
            self.select_frame[kw] = keywords[kw]

        self.select_frame["frameTexture"] = tex
        if aspect_ratio_keeping_scale:
            scale = aspect_ratio_keeping_scale
            self.select_frame["frameSize"] = (
                -scale, scale,
                -vert_aspect_r * scale, vert_aspect_r * scale)


    def add_button(self, text, command, x=0.0, y=0.0, args=None):
        if args is None:
            args = []
        self.funcs.append(command)
        self.args.append(args)
        self.entries.append(DirectButton(**self.button_style, pos=(x, 0, -y), command=self.exec_selection))

        self.entries[-1]["extraArgs"] = [len(self.entries)-1]
        self.entries[-1]["frameTexture"] = self.button_tex
        if self.button_scale:
            self.entries[-1]["frameSize"] = (
                -self.button_scale, self.button_scale,
                -self.button_vert_aspect_r * self.button_scale, self.button_vert_aspect_r * self.button_scale)

        self.set_text(self.entries[-1], text)
        self.select_frame.reparent_to(self.entries[self.active_entry])

        return self.entries[self.active_entry]


    def set_text(self, gui_object, text):
        text_object = DirectLabel(text=text, parent=gui_object, **self.text_style)
        text_object.set_z(-text_object.getHeight() / 2)


    def clear_keys(self):
        if self.use_keyboard:
            base.ignore("arrow_up")
            base.ignore("arrow_down")
            base.ignore("enter")


    def exec_selection(self, entry = None):
        if entry is None:
            self.funcs[self.active_entry](*self.args[self.active_entry])
        else:
            self.funcs[entry](*self.args[entry])
        if self.auto_hide:
            self.hide_menu()


    def select_down(self):
        if self.active_entry == len(self.entries) - 1:
            self.active_entry = 0
        else:
            self.active_entry += 1

        if self.entries[self.active_entry].is_hidden():
            self.select_down()
            return
        self.select_frame.reparent_to(self.entries[self.active_entry])


    def select_up(self):

        if self.active_entry == 0:
            self.active_entry = len(self.entries) - 1
        else:
            self.active_entry -= 1
        if self.entries[self.active_entry].is_hidden():
            self.select_up()
            return
        self.select_frame.reparent_to(self.entries[self.active_entry])


    def hide_menu(self):
        self.clear_keys()
        self.menu_frame.hide()
        self.select_frame.hide()


    def show_menu(self):
        if self.use_keyboard:
            self.clear_keys()
            base.accept("arrow_up", self.select_up)
            base.accept("arrow_down", self.select_down)
            base.accept("enter", self.exec_selection)
        self.menu_frame.show()
        self.select_frame.show()
        seq = Sequence(LerpColorScaleInterval(self.menu_frame, .5, (1, 1, 1, 1)))
        seq.start()
