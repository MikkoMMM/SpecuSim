from direct.gui.DirectGui import DirectLabel


class SpeechBubble:
    """A speech bubble.

    Example:
        speech_bubble = SpeechBubble(someone_who_says_something, 5)
        speech_bubble.set_text("Hello!")
    """


    def __init__(self, parent_node, height):
        self.height = height
        self.speech_bubble = DirectLabel(parent=parent_node, text="", text_wordwrap=10,
                                         relief=None, text_scale=(.3, .3),
                                         pos=(0, 0, height),
                                         frameColor=(.3, .2, .1, .5),
                                         text_frame=(0, 0, 0, 1),
                                         text_bg=(1, 1, 1, 0.4))

        self.speech_bubble.component('text0').textNode.set_card_decal(1)
        self.speech_bubble.set_billboard_point_eye()


    def show(self):
        self.speech_bubble.show()


    def hide(self):
        self.speech_bubble.hide()


    def set_text(self, text):
        self.speech_bubble.setText(text)
        new_height_offset = -self.speech_bubble.getBounds()[2] + self.speech_bubble.getBounds()[3]
        self.speech_bubble.set_z(self.height + new_height_offset)
        self.speech_bubble.updateFrameStyle()  # In case bubble dimensions change
