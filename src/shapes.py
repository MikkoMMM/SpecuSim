from panda3d.bullet import BulletCapsuleShape, BulletBoxShape, BulletSphereShape, BulletCylinderShape, BulletConeShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32
from panda3d.bullet import ZUp
from panda3d.core import Vec3, TransformState, Point3

def createPhysicsCapsule(render, diameter, height):
    shape = BulletCapsuleShape(diameter/2, height-diameter, ZUp)
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createCapsule(render, diameter, height, r=1, g=1, b=1, a=1):
    nodePath = createPhysicsCapsule(render, diameter, height)
    visual = loader.loadModel("models/unit_cylinder.bam")
    visual.setScale(Vec3(diameter, diameter, height))
    visual.reparentTo(nodePath)
    visual.setColor(r, g, b, a)
    return nodePath


def createPhysicsCone(render, diameter, height):
    shape = BulletConeShape(diameter/2, height, ZUp)
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createCone(render, diameter, height, r=1, g=1, b=1, a=1):
    nodePath = createPhysicsCone(render, diameter, height)
    visual = loader.loadModel("models/unit_cone.bam")
    visual.setScale(Vec3(diameter, diameter, height))
    visual.reparentTo(nodePath)
    visual.setColor(r, g, b, a)
    return nodePath


# A cuboid rounded from two sides
# NOTE: width has to be greater than depth
def createPhysicsRoundedBox(render, width, depth, height):
    nodePath = render.attachNewNode(BulletRigidBodyNode())

    shape = BulletBoxShape(Vec3((width-depth)/2, depth/2, height/2))
    nodePath.node().addShape(shape)
    shape = BulletCylinderShape(depth/2, height, ZUp)
    nodePath.node().addShape(shape, TransformState.makePos(Point3((-width+depth)/2, 0, 0)))
    nodePath.node().addShape(shape, TransformState.makePos(Point3((width-depth)/2, 0, 0)))

    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createRoundedBox(render, width, depth, height, r=1, g=1, b=1, a=1):
    nodePath = createPhysicsRoundedBox(render, width, depth, height)
    visual = loader.loadModel("models/unit_cylinder.bam")
    visual.setScale(Vec3(width, depth, height))
    visual.reparentTo(nodePath)
    visual.setColor(r, g, b, a)
    return nodePath


def createPhysicsBox(render, dx, dy, dz):
    shape = BulletBoxShape(Vec3(dx/2, dy/2, dz/2))
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createBox(render, dx, dy, dz, r=1, g=1, b=1, a=1):
    nodePath = createPhysicsBox(render, dx, dy, dz)
    visual = loader.loadModel("models/unit_cube.bam")
    visual.setScale(Vec3(dx, dy, dz))
    visual.reparentTo(nodePath)
    visual.setColor(r, g, b, a)
    return nodePath


def createPhysicsSphere(render, diameter):
    shape = BulletSphereShape(diameter/2)
    nodePath = render.attachNewNode(BulletRigidBodyNode())
    nodePath.setCollideMask(BitMask32.bit(1))
    nodePath.node().addShape(shape)
    nodePath.node().setAngularDamping(0.9)
    nodePath.node().setFriction(0.8)
    nodePath.node().setRestitution(0.0)
    return nodePath

def createSphere(render, diameter, r=1, g=1, b=1, a=1):
    nodePath = createPhysicsSphere(render, diameter)
    visual = loader.loadModel("models/unit_sphere.bam")
    visual.setScale(Vec3(diameter, diameter, diameter))
    visual.reparentTo(nodePath)
    visual.setColor(r, g, b, a)
    return nodePath
