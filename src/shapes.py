from panda3d.bullet import BulletCapsuleShape, BulletBoxShape, BulletSphereShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32
from panda3d.bullet import ZUp
from panda3d.core import Vec3

def createCapsule(render, diameter, height):
    shape = BulletCapsuleShape(diameter/2, height-diameter, ZUp)
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createBox(render, dx, dy, dz):
    shape = BulletBoxShape(Vec3(dx, dy, dz))
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createSphere(render, radius):
    shape = BulletSphereShape(radius)
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath
