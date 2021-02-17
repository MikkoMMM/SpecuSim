from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import ZUp
from src.shapes import createCapsule
from src.leg import Leg
from src.utils import angleDiff
import time
from math import degrees

class Humanoid():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # terrainBulletNode: A bullet physics node for the terrain mesh
    # TODO: explanations for optional arguments
    def __init__(self, render, world, terrainBulletNode, name="", sex='', height=0, mass=0, age=0):
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
        self.terrainBulletNode = terrainBulletNode
        self.lastStepTime = 0
        self.stepCounter = 0

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
        self.chest.node().setLinearDamping(0.5)
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
        self.lowerTorso.node().setLinearDamping(0.5)
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

        frameA = TransformState.makePosHpr(Point3(-self.pelvisWidth/4, 0, -0.25), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.leftLeg.thighLength/2), Vec3(0, 0, 0))

        self.leftLegConstraint = BulletGenericConstraint(self.lowerTorso.node(), self.leftLeg.thigh.node(), frameA, frameB, True)
        self.leftLegConstraint.setDebugDrawSize(2.0)
        self.leftLegConstraint.setAngularLimit(0, -90, 60)
        self.leftLegConstraint.setAngularLimit(1, 0, 0)
        self.leftLegConstraint.setAngularLimit(2, -180, 180)
        self.world.attachConstraint(self.leftLegConstraint, linked_collision=True)
        self.leftLegYHinge = self.leftLegConstraint.getRotationalLimitMotor(0)
        self.leftLegYHinge.setMotorEnabled(True)
        self.leftLegYHinge.setMaxMotorForce(200)
        self.leftLegZHinge = self.leftLegConstraint.getRotationalLimitMotor(2)
        self.leftLegZHinge.setMotorEnabled(True)
        self.leftLegZHinge.setMaxMotorForce(200)


        self.rightLeg = Leg(self.render, self.world, 0.8, self.pelvisWidth/2-0.01, (self.pelvisWidth/2-0.01)*0.8)

        frameA = TransformState.makePosHpr(Point3(self.pelvisWidth/4, 0, -0.25), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.leftLeg.thighLength/2), Vec3(0, 0, 0))

        self.rightLegConstraint = BulletGenericConstraint(self.lowerTorso.node(), self.rightLeg.thigh.node(), frameA, frameB, True)
        self.rightLegConstraint.setDebugDrawSize(2.0)
        self.rightLegConstraint.setAngularLimit(0, -90, 60)
        self.rightLegConstraint.setAngularLimit(1, 0, 0)
        self.rightLegConstraint.setAngularLimit(2, -180, 180)
        self.world.attachConstraint(self.rightLegConstraint, linked_collision=True)
        self.rightLegYHinge = self.rightLegConstraint.getRotationalLimitMotor(0)
        self.rightLegYHinge.setMotorEnabled(True)
        self.rightLegYHinge.setMaxMotorForce(200)
        self.rightLegZHinge = self.rightLegConstraint.getRotationalLimitMotor(2)
        self.rightLegZHinge.setMotorEnabled(True)
        self.rightLegZHinge.setMaxMotorForce(200)

        self.leftKneeYHinge = self.leftLeg.knee.getRotationalLimitMotor(0)
        self.rightKneeYHinge = self.rightLeg.knee.getRotationalLimitMotor(0)
        self.leftKneeYHinge.setMaxMotorForce(200)
        self.rightKneeYHinge.setMaxMotorForce(200)

        self.leftKneeZHinge = self.leftLeg.knee.getRotationalLimitMotor(2)
        self.rightKneeZHinge = self.rightLeg.knee.getRotationalLimitMotor(2)
        self.leftKneeZHinge.setMotorEnabled(True)
        self.rightKneeZHinge.setMotorEnabled(True)
        self.leftKneeZHinge.setMaxMotorForce(200)
        self.rightKneeZHinge.setMaxMotorForce(200)
        self.leftLeg.knee.setAngularLimit(2, -180, 180)
        self.rightLeg.knee.setAngularLimit(2, -180, 180)


    def testIfNearGround(self, bodypart, distance):
        pFrom = bodypart.getPos()
        rc_result = self.world.rayTestAll(pFrom + Vec3(0, 0, distance), pFrom - Vec3(0, 0, distance))

        for hit in rc_result.getHits():
            if hit.getNode() == self.terrainBulletNode:
                return True
        return False

    # A really hacky physics-driven movement implementation.
    # seconds: roughly how long each step should take
    # angle: angle in which to walk. For instance, zero is ahead, -90 is left and 90 is right.
    def takeStep(self, seconds, angle):
        moveMass = 50

        if abs(angleDiff(degrees(self.leftLegConstraint.getAngle(2)),angle)) > 90:
            self.inverted = True
            angle -= 180
            leftLegAngleError = angleDiff(degrees(self.leftLegConstraint.getAngle(2)),angle)
        else:
            self.inverted = False

        # A way to support an arbitrary walking angle
        self.leftLegZHinge.setTargetVelocity(angleDiff(degrees(self.leftLegConstraint.getAngle(2)),angle)/15)
        self.rightLegZHinge.setTargetVelocity(angleDiff(degrees(self.rightLegConstraint.getAngle(2)),angle)/5)
        self.leftKneeZHinge.setTargetVelocity(angleDiff(degrees(self.leftLeg.knee.getAngle(2)),-angle)/5)
        self.rightKneeZHinge.setTargetVelocity(angleDiff(degrees(self.rightLeg.knee.getAngle(2)),-angle)/5)

        #Enable ragdoll physics for the knee
        self.leftKneeYHinge.setMotorEnabled(False)
        self.rightKneeYHinge.setMotorEnabled(False)

        if (not self.inverted and self.leftLegConstraint.getAngle(0) <= self.rightLegConstraint.getAngle(0)) or self.inverted and self.leftLegConstraint.getAngle(0) > self.rightLegConstraint.getAngle(0):
            self.leftLeg.foot.node().setMass(moveMass)
            self.rightLeg.foot.node().setMass(1)
        else:
            self.rightLeg.foot.node().setMass(moveMass)
            self.leftLeg.foot.node().setMass(1)

        if self.stepCounter == 1:
            if time.time() < self.lastStepTime + seconds/2: # If we were standing still, it's a half-step
                return
        elif time.time() < self.lastStepTime + seconds:
            return
        self.stepCounter += 1

        self.lastStepTime = time.time()

        if not self.inverted and self.leftLeg.foot.node().getMass() == moveMass or self.inverted and self.rightLeg.foot.node().getMass() == moveMass:
            self.leftLegYHinge.setTargetVelocity(3/seconds)
            self.rightLegYHinge.setTargetVelocity(-3/seconds)
        else:
            self.leftLegYHinge.setTargetVelocity(-3/seconds)
            self.rightLegYHinge.setTargetVelocity(3/seconds)

    def standStill(self):
        self.neutralPosition()

    def neutralPosition(self):
        self.rightLeg.foot.node().setMass(1)
        self.leftLeg.foot.node().setMass(1)

        self.leftLegYHinge.setTargetVelocity(-self.leftLegConstraint.getAngle(0)*5)
        self.rightLegYHinge.setTargetVelocity(-self.rightLegConstraint.getAngle(0)*5)

        self.leftKneeYHinge.setMotorEnabled(True)
        self.rightKneeYHinge.setMotorEnabled(True)
        self.leftKneeYHinge.setTargetVelocity(-self.leftLeg.knee.getAngle(0)*5)
        self.rightKneeYHinge.setTargetVelocity(-self.rightLeg.knee.getAngle(0)*5)
        self.stepCounter = 0
