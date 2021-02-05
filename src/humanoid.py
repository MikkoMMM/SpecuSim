from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint
from panda3d.bullet import ZUp
from src.shapes import createCapsule
from src.leg import Leg

class Humanoid():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # TODO: explanations for optional arguments
    def __init__(self, render, world, name="", sex='', height=0, mass=0, age=0):
        self.name = name
        self.sex = sex or ''
        self.height = height or 170
        self.headHeight = height/7.5
        self.chestWidth = 0.38
        self.pelvisWidth = 0.38
        self.chestToHeightRatio = 0
        self.mass = mass
        self.render = render
        self.world = world

        axisA = Vec3(1, 0, 0)

        # Organism's shape and collision boxes
        # The chest's collision box has the tallness of the entire organism, divided by two
        size = Vec3(self.chestWidth, 0.2, 0.5)
        shape = BulletCylinderShape(size/2)
        self.chest = self.render.attachNewNode(BulletRigidBodyNode())
        self.chest.setCollideMask(BitMask32.bit(0))
        self.chest.node().setMass(40.0)
        self.chest.node().addShape(shape)
        self.chest.node().setAngularFactor(Vec3(0.15,0.05,0.1))
        self.chest.node().setAngularDamping(0.9)
        self.chest.node().setFriction(0.8)
        self.chest.node().setRestitution(0.0)
        self.chest.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(self.chest.node())
        chestVisual = loader.loadModel("models/unit_cylinder.bam")
        chestVisual.setScale(size)
        chestVisual.reparentTo(self.chest)

        size = Vec3(self.pelvisWidth, 0.2, 0.5)
        shape = BulletCylinderShape(size/2)
        self.lowerTorso = self.render.attachNewNode(BulletRigidBodyNode())
        self.lowerTorso.setCollideMask(BitMask32.bit(0))
        self.lowerTorso.node().setMass(40.0)
        self.lowerTorso.node().addShape(shape)
        self.lowerTorso.node().setAngularFactor(Vec3(0,0,0.1))
        self.lowerTorso.node().setAngularDamping(0.9)
        self.lowerTorso.node().setFriction(0.8)
        self.lowerTorso.node().setRestitution(0.0)
        self.lowerTorso.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(self.lowerTorso.node())
        lowerTorsoVisual = loader.loadModel("models/unit_cylinder.bam")
        lowerTorsoVisual.setScale(size)
        lowerTorsoVisual.reparentTo(self.lowerTorso)
        
        pivotA = Point3(0, 0, -0.25)
        pivotB = Point3(0, 0, 0.25)

        frameA = TransformState.makePosHpr(Point3(0, 0, -0.25), Vec3(0, 0, -90))
        frameB = TransformState.makePosHpr(Point3(0, 0, 0.25), Vec3(0, 0, -90))

        swing1 = 10 # leaning forward/backward degrees
        swing2 = 5 # leaning side to side degrees
        twist = 30 # degrees

        cs = BulletConeTwistConstraint(self.chest.node(), self.lowerTorso.node(), frameA, frameB)
        cs.setDebugDrawSize(2.0)
        cs.setLimit(swing1, swing2, twist, softness=0.9, bias=0.3, relaxation=1.0)
        world.attachConstraint(cs, linked_collision=True)

        
        self.leftLeg = Leg(self.render, self.world, 0.8, self.pelvisWidth/2-0.01, (self.pelvisWidth/2-0.01)*0.8)

        pivotA = Point3(-self.pelvisWidth/8, 0, -0.25)
        pivotB = Point3(self.pelvisWidth/8, 0, self.leftLeg.thighLength/2)

        self.leftLegConstraint = BulletHingeConstraint(self.lowerTorso.node(), self.leftLeg.thigh.node(), pivotA, pivotB, axisA, axisA, True)
        self.leftLegConstraint.setDebugDrawSize(2.0)
        self.leftLegConstraint.setLimit(-60, 90, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(self.leftLegConstraint, linked_collision=True)


        self.rightLeg = Leg(self.render, self.world, 0.8, self.pelvisWidth/2-0.01, (self.pelvisWidth/2-0.01)*0.8)

        pivotA = Point3(self.pelvisWidth/8, 0, -0.25)
        pivotB = Point3(-self.pelvisWidth/8, 0, self.rightLeg.thighLength/2)

        self.rightLegConstraint = BulletHingeConstraint(self.lowerTorso.node(), self.rightLeg.thigh.node(), pivotA, pivotB, axisA, axisA, True)
        self.rightLegConstraint.setDebugDrawSize(2.0)
        self.rightLegConstraint.setLimit(-60, 90, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(self.rightLegConstraint, linked_collision=True)
