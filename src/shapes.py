from panda3d.bullet import BulletCapsuleShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32
from panda3d.bullet import ZUp

def createCapsule(render, diameter, height):
    shape = BulletCapsuleShape(diameter/2, height-diameter, ZUp)
    capsule = render.attachNewNode(BulletRigidBodyNode())
    capsule.setCollideMask(BitMask32.bit(1))
    capsule.node().addShape(shape)
    capsule.node().setAngularDamping(0.9)
    capsule.node().setFriction(0.8)
    capsule.node().setRestitution(0.0)
    return capsule
