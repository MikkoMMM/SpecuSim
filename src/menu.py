# Credit: RenderPipeline contributors

from sys import exit

from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectGuiBase import DGG
from direct.gui.DirectLabel import DirectLabel
from direct.interval.LerpInterval import LerpColorScaleInterval
from direct.interval.MetaInterval import Sequence
from panda3d.core import TextNode, PNMImage, Filename, Texture


def set_centered_text(gui_object, text, scale=0.5, fg=(0.2, 0.2, 0.2, 1)):
    text_object = DirectLabel(text=text,
                              text_fg=fg,
                              relief=None,
                              text_align=TextNode.ACenter, text_scale=scale,
                              parent=gui_object)

    text_object.set_pos(0, 0, -text_object.getHeight() / 2)


class Menu:
    def __init__(self, menu_tex_img, size_x=1, size_y=1, frame_color=(1, 1, 1, 1)):
        kx = menu_tex_img.get_x_size()
        ky = menu_tex_img.get_y_size()
        menu_tex = Texture("menu texture")
        menu_tex.load(menu_tex_img)

        wx = kx / ky

        self.my_frame = DirectFrame(frameColor=frame_color,
                                    frameSize=(-size_x * wx, size_x * wx, -size_y, size_y))

        self.my_frame["frameTexture"] = menu_tex
        self.my_frame.reparent_to(base.aspect2d)
        self.my_frame.set_pos(0, 0, 0)
        self.my_frame.set_transparency(True)
        self.my_frame.hide()

        self.entries = []
        self.funcs = []
        self.args = []

        self.button_tex = Texture("button texture")
        self.button_vert_aspect_r = 1
        self.set_button_texture(PNMImage(Filename("textures/empty_button_52.png")))

        self.button_style = {
            "frameColor": (1, 1, 1, 1),
            "relief": DGG.FLAT,
            "rolloverSound": None,
            "clickSound": None,
            "parent": self.my_frame,
            "scale": 0.1,
        }

        self.active_entry = 0
        self.select_frame = DirectFrame(frameColor=(1, 1, 1, 1), frameSize=(-2, 2, -0.4, 0.4), frameTexture="textures/select.png")
        self.select_frame.hide()

    def set_button_texture(self, image):
        kx = image.get_x_size()
        ky = image.get_y_size()
        self.button_vert_aspect_r = ky / kx
        self.button_tex.load(image)

    def change_button_style(self, img=None, **keywords):
        if img:
            set_button_texture(img)
        for kw in keywords:
            self.button_style[kw] = keywords[kw]

    def add_button(self, text, command, x=0.0, y=0.0, args=None):
        if args is None:
            args = []
        self.entries.append(DirectButton(**self.button_style, pos=(x, 0, -y)))

        self.entries[-1]["frameTexture"] = self.button_tex
        self.entries[-1]["frameSize"] = (-2, 2, -self.button_vert_aspect_r * 2, self.button_vert_aspect_r * 2)
        self.funcs.append(command)
        self.args.append(args)

        set_centered_text(self.entries[-1], text)

        self.select_frame.reparent_to(self.entries[self.active_entry])

    def clear_keys(self):
        base.ignore("arrow_up")
        base.ignore("arrow_down")
        base.ignore("arrow_left")
        base.ignore("arrow_right")
        base.ignore("s")
        base.ignore("w")
        base.ignore("escape")
        base.ignore("enter")

    def exec_selection(self):
        self.funcs[self.active_entry](*self.args[self.active_entry])

    #        self.entries[self.active_entry]["command"]()

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
        self.my_frame.hide()

    #        seq= Sequence( LerpColorScaleInterval(self.my_frame, 0.4 ,(1,1,1,0)) , Func(self.my_frame.hide) )
    #        seq.start()

    def show_menu(self):
        self.clear_keys()
        base.accept("arrow_up", self.select_up)
        base.accept("arrow_down", self.select_down)
        base.accept("w", self.select_up)
        base.accept("s", self.select_down)
        base.accept("escape", exit)
        base.accept("enter", self.exec_selection)
        self.my_frame.show()
        self.select_frame.show()
        seq = Sequence(LerpColorScaleInterval(self.my_frame, .5, (1, 1, 1, 1)))
        seq.start()
