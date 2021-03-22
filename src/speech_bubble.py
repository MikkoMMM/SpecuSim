from direct.gui.DirectGui import DirectLabel


class SpeechBubble():
    def __init__(self, parent_node, height):
        self.speech_bubble = DirectLabel(parent=parent_node, text="", text_wordwrap=10,
                                         relief=None, text_scale=(.5, .5),
                                         pos=(0, 0, height),
                                         frameColor=(.3, .2, .1, .5),
                                         text_frame=(0, 0, 0, 1),
                                         text_bg=(1, 1, 1, 0.4))

        self.speech_bubble.component('text0').textNode.set_card_decal(1)
        self.speech_bubble.set_billboard_point_eye()

    def set_text(self, text):
        self.speech_bubble['text'] = text
