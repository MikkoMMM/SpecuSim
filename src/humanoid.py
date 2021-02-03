from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3
from panda3d.bullet import BulletHingeConstraint
from panda3d.bullet import ZUp

class Humanoid():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # TODO: explanations for optional arguments
    def __init__(self, render, world, name="", sex=0, height=0, mass=0):
        self.name = name
        self.sex = sex
        self.height = height
        self.mass = mass
        self.render = render
        self.world = world

        # Organism's shape and collision boxes
        # The torso's collision box has the tallness of the entire organism, divided by two
        shape = BulletCylinderShape(Vec3(0.5, 0.5, 0.5))
        self.torso = self.render.attachNewNode(BulletRigidBodyNode())
        self.torso.setCollideMask(BitMask32.bit(0))
        self.torso.node().setMass(80.0)
        self.torso.node().addShape(shape)
        self.torso.node().setAngularFactor(Vec3(0,0,0.1))
        self.torso.node().setAngularDamping(0.9)
        self.torso.node().setFriction(0.8)
        self.torso.node().setRestitution(0.0)
        self.torso.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(self.torso.node())
        torsoVisual = loader.loadModel("models/unit_cylinder.bam")
        torsoVisual.reparentTo(self.torso)
        
        self.leftLeg = self.createLeg(0.45, 1)

        pivotA = Point3(0, 0, -0.5)
        pivotB = Point3(0, 0, 0.5)
        axisA = Vec3(1, 0, 0)
        axisB = Vec3(1, 0, 0)

        hinge = BulletHingeConstraint(self.torso.node(), self.leftLeg.node(), pivotA, pivotB, axisA, axisB, True)
        hinge.setDebugDrawSize(2.0)
        hinge.setLimit(-60, 90, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(hinge, linked_collision=True)

        hinge.enableMotor(True)
        hinge.setMotorTarget(80, 1)

    def createLeg(self, diameter, height):
        shape = BulletCapsuleShape(diameter/2, height-diameter, ZUp)
        leg = self.render.attachNewNode(BulletRigidBodyNode())
        leg.setCollideMask(BitMask32.bit(1))
        leg.node().setMass(10.0)
        leg.node().addShape(shape)
        leg.node().setAngularDamping(0.9)
        leg.node().setFriction(0.8)
        leg.node().setRestitution(0.0)
        self.world.attachRigidBody(leg.node())
        legVisual = loader.loadModel("models/unit_cylinder.bam")
        legVisual.setScale(Vec3(diameter, diameter, height))
        legVisual.reparentTo(leg)
        return leg
