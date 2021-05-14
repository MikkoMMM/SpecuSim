from src.shapes import create_cone
from panda3d.core import Vec3, Point3
from panda3d.core import BitMask32
from math import radians, sin, cos

class Sword():
    def __init__(self, world, main_body, length=1.3):
        self.main_body = main_body
        self.length = length
        self.root = create_cone(0.05, -self.length, r=0.7, g=0.7, b=0.7)
        self.root.node().set_mass(1.5)
        # self.root.node().set_angular_factor(Vec3(0.5,0.5,0.5))
        # self.root.node().set_linear_damping(0.5)
        self.root.set_collide_mask(BitMask32.allOn())
        world.attach(self.root.node())

    def getAttachmentInfo(self):
        return self, self.root, Point3(0, 0, self.length / 2 - 0.1)
