from src.shapes import createCone
from panda3d.core import Vec3, Point3
from panda3d.core import BitMask32
from math import radians, sin, cos

class Sword():
    def __init__(self, render, world, mainBody, length=1.3):
        self.mainBody = mainBody
        self.length = length
        self.root = createCone(render, 0.05, self.length, r=0.7, g=0.7, b=0.7)
        self.root.node().setMass(1.5)
        self.root.node().setAngularFactor(Vec3(0.5,0.5,0.5))
        self.root.node().setLinearDamping(0.5)
        self.root.setCollideMask(BitMask32.allOn())
        world.attach(self.root.node())
        
    def getAttachmentInfo(self):
        return (self, self.root, Point3(0,0,-self.length/2+0.1))

    def setHpr(self, heading, pitch, roll):
        H = radians(heading+90)
        P = radians(pitch)
        x = cos(H) * cos(P)
        y = sin(H) * cos(P)
        z = sin(P)

        force = 1000
        self.root.node().applyCentralForce(Vec3(force*x,force*y,force*z))
        self.mainBody.node().applyCentralForce(Vec3(-force*x,-force*y,-force*z))
