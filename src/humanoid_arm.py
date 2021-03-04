from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import ZUp
from src.shapes import createCapsule

class HumanoidArm():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # upperArmDiameter: upperArm's diameter
    # forearmDiameter: forearm's diameter
    # height: arm's total height
    def __init__(self, render, world, height, upperArmDiameter, forearmDiameter, rightArm, startPosition, startHeading):
        self.render = render
        self.world = world

        self.upperArmLength = height*50/100
        self.forearmLength = height*50/100
        self.upperArmDiameter = upperArmDiameter

        self.upperArm = createCapsule(self.render, self.upperArmDiameter, self.upperArmLength)
        self.upperArm.node().setMass(3.0)
        self.world.attach(self.upperArm.node())


        self.forearm = createCapsule(self.render, forearmDiameter, self.forearmLength)
        self.forearm.setCollideMask(BitMask32.bit(3))
        self.forearm.node().setMass(2.0)
        self.world.attach(self.forearm.node())

        frameA = TransformState.makePosHpr(Point3(0,0,-self.upperArmLength/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0,0,self.forearmLength/2), Vec3(0, 0, 0))

        self.elbow = BulletGenericConstraint(self.upperArm.node(), self.forearm.node(), frameA, frameB, True)

        self.elbow.setAngularLimit(0, -165, 0)
        if rightArm:
            self.elbow.setAngularLimit(1, -30, 0)
        else:
            self.elbow.setAngularLimit(1, 0, 30)

        self.elbow.setAngularLimit(2, 0, 0)
        self.elbow.setDebugDrawSize(0.5)
        self.world.attachConstraint(self.elbow, linked_collision=True)

        self.upperArm.setPosHpr(startPosition, startHeading)
        self.forearm.setPosHpr(startPosition, startHeading)
    
    def grab(self, attachmentInfo):
        if len(attachmentInfo) >= 3:
            self.grabForReal(attachmentInfo[0], attachmentInfo[1], grabAngle=attachmentInfo[2])
        else:
            self.grabForReal(attachmentInfo[0], attachmentInfo[1])

    def grabForReal(self, target, grabPosition, grabAngle=Vec3(0, 0, 0)):
        frameA = TransformState.makePosHpr(Point3(0,0,-self.forearmLength/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(grabPosition, grabAngle)

        self.hand = BulletGenericConstraint(self.forearm.node(), target.node(), frameA, frameB, True)
        self.hand.setDebugDrawSize(0.5)
        self.hand.setAngularLimit(0, -180, 180)
        self.hand.setAngularLimit(1, -180, 180)
        self.hand.setAngularLimit(2, -180, 180)
        self.world.attachConstraint(self.hand, linked_collision=True)

    def setPos(self, newPos):
        self.upperArm.setPos(newPos)
        self.forearm.setPos(newPos)
