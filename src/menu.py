# Credit: RenderPipeline contributors

from sys import exit

from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectGuiBase import DGG
from direct.gui.DirectLabel import DirectLabel
from direct.interval.FunctionInterval import Func
from direct.interval.LerpInterval import LerpColorScaleInterval
from direct.interval.MetaInterval import Sequence
from panda3d.core import SamplerState, TextNode, PNMImage, Filename, Texture


def set_centered_text(gui_object, text, scale=14, fg=(0.2, 0.2, 0.2, 1)):
    text_object = DirectLabel(text=text,
                              text_fg=fg,
                              relief=None,
                              text_align=TextNode.ACenter, text_scale=scale,
                              parent=gui_object)

    text_object.set_pos(0, 0, -text_object.getHeight() / 2)


class Menu:
    def __init__(self, main):
        self.main = main

        menu_tex_img = PNMImage(Filename("textures/menu.jpg"))
        kx = menu_tex_img.get_x_size()
        ky = menu_tex_img.get_y_size()
        menu_tex = Texture("texture name")
        menu_tex.load(menu_tex_img)

        self.my_frame = DirectFrame(frameColor=(1, 1, 1, 1),
                                    frameSize=(-kx/ky, kx/ky, -1, 1))

        self.my_frame["frameTexture"] = menu_tex
        self.my_frame.reparent_to(base.aspect2d)
        self.my_frame.set_pos(0, 0, 0)
        self.my_frame.set_transparency(True)

        self.entries = []

        self.entries.append(DirectButton(
            frameTexture="textures/empty_button.png",
            frameColor=(1, 1, 1, 1),
            frameSize=(-1, 1, -0.4, 0.4),
            command=self.main.start_game,
            relief=DGG.FLAT,
            rolloverSound=None,
            clickSound=None,
            parent=self.my_frame,
            scale=0.003,
            pos=(0, 0, 0.1)
        ))
        set_centered_text(self.entries[-1], "No Add-Ons")
        self.entries[-1].set_transparency(1)

        self.entries.append(DirectButton(
            frameTexture="textures/empty_button.png",
            frameColor=(1, 1, 1, 1),
            frameSize=(-1, 1, -0.4, 0.4),
            command=self.main.start_with_nlp,
            relief=DGG.FLAT,
            rolloverSound=None,
            clickSound=None,
            parent=self.my_frame,
            scale=0.003,
            pos=(0, 0, 0.0)
        ))
        set_centered_text(self.entries[-1], "Language AI")
        self.entries[-1].set_transparency(1)

        self.entries.append(DirectButton(
            frameTexture="textures/empty_button.png",
            frameColor=(1, 1, 1, 1),
            frameSize=(-1, 1, -0.4, 0.4),
            command=exit,
            relief=DGG.FLAT,
            rolloverSound=None,
            clickSound=None,
            parent=self.my_frame,
            scale=0.003,
            pos=(0, 0, -0.1)
        ))

        set_centered_text(self.entries[-1], "Exit Game")
        self.entries[-1].set_transparency(1)

        self.active_entry = 1
        self.select_frame = DirectFrame(frameColor=(1, 1, 1, 1), frameSize=(-64, 64, -15, 15), frameTexture="textures/select.png")
        self.select_frame.set_transparency(1)
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
        self.entries[self.active_entry]["command"]()

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
        seq = Sequence(LerpColorScaleInterval(self.my_frame, .5, (1, 1, 1, 1)))
        seq.start()
