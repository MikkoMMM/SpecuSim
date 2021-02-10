from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint
from panda3d.bullet import ZUp
from src.shapes import createCapsule, createBox

class Leg():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # thighDiameter: thigh's diameter
    # lowerLegDiameter: lower leg's diameter
    # height: leg's total height
    def __init__(self, render, world, height, thighDiameter, lowerLegDiameter):
        self.render = render
        self.world = world

        axisA = Vec3(1, 0, 0)
        self.thighLength = height*59/109
        self.lowerLegLength = height*37/109
        self.footHeight = height - self.thighLength - self.lowerLegLength

        self.thigh = createCapsule(self.render, thighDiameter, self.thighLength)
        self.thigh.node().setMass(10.0)
        self.world.attachRigidBody(self.thigh.node())
        visual = loader.loadModel("models/unit_cylinder.bam")
        visual.setScale(Vec3(thighDiameter, thighDiameter, self.thighLength))
        visual.reparentTo(self.thigh)


        self.lowerLeg = createCapsule(self.render, lowerLegDiameter, self.lowerLegLength)
        self.lowerLeg.node().setMass(5.0)
        self.world.attachRigidBody(self.lowerLeg.node())
        visual = loader.loadModel("models/unit_cylinder.bam")
        visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter, self.lowerLegLength))
        visual.reparentTo(self.lowerLeg)

        pivotA = Point3(0, 0, -self.thighLength/2)
        pivotB = Point3(0, 0, self.lowerLegLength/2)

        self.kneeConstraint = BulletHingeConstraint(self.thigh.node(), self.lowerLeg.node(), pivotA, pivotB, axisA, axisA, True)
        self.kneeConstraint.setDebugDrawSize(2.0)
        self.kneeConstraint.setLimit(-45, 0, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(self.kneeConstraint, linked_collision=True)
#        self.kneeConstraint.enableMotor(True)


        self.foot = createBox(self.render, lowerLegDiameter, lowerLegDiameter*2.2, self.footHeight)
        self.foot.node().setMass(1.0)
        self.world.attachRigidBody(self.foot.node())
        visual = loader.loadModel("models/unit_cube.bam")
        visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter*2.2, self.footHeight))
        visual.reparentTo(self.foot)

        pivotA = Point3(0, lowerLegDiameter/6, -self.lowerLegLength/2)
        pivotB = Point3(0, -lowerLegDiameter/6, self.footHeight/2)

        self.heelConstraint = BulletHingeConstraint(self.lowerLeg.node(), self.foot.node(), pivotA, pivotB, axisA, axisA, True)
        self.heelConstraint.setDebugDrawSize(2.0)
        self.heelConstraint.setLimit(0, 45, softness=0.9, bias=0.3, relaxation=1.0)
        self.world.attachConstraint(self.heelConstraint, linked_collision=True)
        #self.heelConstraint.enableMotor(True)
