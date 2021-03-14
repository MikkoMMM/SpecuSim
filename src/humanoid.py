from panda3d.bullet import BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState, RigidBodyCombiner, NodePath
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import ZUp
from src.shapes import createSphere, createRoundedBox
from src.humanoid_leg import HumanoidLeg
from src.humanoid_arm import HumanoidArm
from src.utils import angleDiff, normalizeAngle, getObjectGroundZPos
import time
from math import degrees, radians, sqrt, pi, cos, sin, copysign

class Humanoid():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # startPosition: where to spawn the humanoid
    # startHeading: an optional starting heading
    # TODO: explanations for optional arguments
    def __init__(self, render, world, terrainBulletNode, startPosition, startHeading=Vec3(0,0,0), name="", sex='', height=1.7, age=0):
        self.name = name
        self.sex = sex or ''
        self.height = height
        self.headHeight = self.height/7
        self.chestWidth = 0.38
        self.pelvisWidth = 0.38
        self.chestToHeightRatio = 0
        self.render = render
        self.world = world
        self.terrainBulletNode = terrainBulletNode
        self.lastStepTime = 1
        self.lowerTorsoHeight = 1.3*(self.height/7)
        self.chestHeight = 1.5*(self.height/7)
        self.legHeight = self.height - self.headHeight - self.lowerTorsoHeight - self.chestHeight
        self.armHeight = self.legHeight*1
        self.legYLimit = 60
        self.inverted = False
        self.inLeftHand = None
        self.inRightHand = None

        axisA = Vec3(1, 0, 0)

        # Organism's shape and collision boxes
        self.chest = createRoundedBox(self.render, self.chestWidth, 0.2, self.chestHeight)
        self.chest.node().setMass(40.0)
        self.chest.node().setAngularFactor(Vec3(0.15,0.05,0.1))
        self.chest.node().setLinearDamping(0.5)
        self.chest.setCollideMask(BitMask32.bit(3))
        self.world.attach(self.chest.node())
        self.chest.node().setAngularSleepThreshold(0.05)

        self.lowerTorso = createRoundedBox(self.render, self.chestWidth, 0.2, self.chestHeight)
        self.lowerTorso.node().setMass(40.0)
        self.lowerTorso.node().setAngularFactor(Vec3(0,0,0.1))
        self.lowerTorso.node().setLinearDamping(0.5)
        self.lowerTorso.node().setAngularSleepThreshold(0) # For whatever reason, sleep seems to freeze the whole character if still
        self.lowerTorso.setCollideMask(BitMask32.bit(3))
        self.world.attach(self.lowerTorso.node())

        frameA = TransformState.makePosHpr(Point3(0, 0, -self.chestHeight/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.lowerTorsoHeight/2), Vec3(0, 0, 0))

        swing1 = 10 # leaning forward/backward degrees
        swing2 = 5 # leaning side to side degrees
        twist = 30 # degrees

        cs = BulletConeTwistConstraint(self.chest.node(), self.lowerTorso.node(), frameA, frameB)
        cs.setDebugDrawSize(0.5)
        cs.setLimit(twist, swing2, swing1, softness=0.1, bias=1.0, relaxation=1.0)
        world.attachConstraint(cs, linked_collision=True)

        
        self.leftLeg = HumanoidLeg(self.render, self.world, self.legHeight, self.pelvisWidth/2-0.01, (self.pelvisWidth/2-0.01)*self.legHeight, startPosition, startHeading)

        frameA = TransformState.makePosHpr(Point3(-self.pelvisWidth/4, 0, -self.lowerTorsoHeight/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.leftLeg.thighLength/2), Vec3(0, 0, 0))

        self.leftLegConstraint = BulletGenericConstraint(self.lowerTorso.node(), self.leftLeg.thigh.node(), frameA, frameB, True)
        self.leftLegConstraint.setDebugDrawSize(0.5)
        self.leftLegConstraint.setAngularLimit(0, -self.legYLimit, self.legYLimit)
        self.leftLegConstraint.setAngularLimit(1, 0, 0)
        self.leftLegConstraint.setAngularLimit(2, -180, 180)
        self.world.attachConstraint(self.leftLegConstraint, linked_collision=True)
        '''
        self.leftLegYHinge = self.leftLegConstraint.getRotationalLimitMotor(0)
        self.leftLegYHinge.setMotorEnabled(False)
        self.leftLegYHinge.setMaxMotorForce(5000)
        self.leftLegYHinge.setMaxLimitForce(5000)
        self.leftLegYHinge.setStopCfm(0)
        self.leftLegYHinge.setDamping(0)
        self.leftLegYHinge.setBounce(0)
        '''
        self.leftLegZHinge = self.leftLegConstraint.getRotationalLimitMotor(2)
        self.leftLegZHinge.setMotorEnabled(True)
        self.leftLegZHinge.setMaxMotorForce(200)
        self.leftLegZHinge.setMaxLimitForce(400)


        self.rightLeg = HumanoidLeg(self.render, self.world, self.legHeight, self.pelvisWidth/2-0.01, (self.pelvisWidth/2-0.01)*self.legHeight, startPosition, startHeading)

        frameA = TransformState.makePosHpr(Point3(self.pelvisWidth/4, 0, -self.lowerTorsoHeight/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.leftLeg.thighLength/2), Vec3(0, 0, 0))

        self.rightLegConstraint = BulletGenericConstraint(self.lowerTorso.node(), self.rightLeg.thigh.node(), frameA, frameB, True)
        self.rightLegConstraint.setDebugDrawSize(0.5)
        self.rightLegConstraint.setAngularLimit(0, -self.legYLimit, self.legYLimit)
        self.rightLegConstraint.setAngularLimit(1, 0, 0)
        self.rightLegConstraint.setAngularLimit(2, -180, 180)
        self.world.attachConstraint(self.rightLegConstraint, linked_collision=True)
        '''
        self.rightLegYHinge = self.rightLegConstraint.getRotationalLimitMotor(0)
        self.rightLegYHinge.setMotorEnabled(False)
        self.rightLegYHinge.setMaxMotorForce(5000)
        self.rightLegYHinge.setMaxLimitForce(5000)
        self.rightLegYHinge.setStopCfm(0)
        self.rightLegYHinge.setDamping(0)
        self.rightLegYHinge.setBounce(0)
        '''
        self.rightLegZHinge = self.rightLegConstraint.getRotationalLimitMotor(2)
        self.rightLegZHinge.setMotorEnabled(True)
        self.rightLegZHinge.setMaxMotorForce(200)
        self.rightLegZHinge.setMaxLimitForce(400)

        self.leftKneeYHinge = self.leftLeg.knee.getRotationalLimitMotor(0)
        self.rightKneeYHinge = self.rightLeg.knee.getRotationalLimitMotor(0)
        self.leftKneeYHinge.setMaxMotorForce(200)
        self.rightKneeYHinge.setMaxMotorForce(200)
        self.leftKneeYHinge.setMaxLimitForce(400)
        self.rightKneeYHinge.setMaxLimitForce(400)

        self.leftKneeZHinge = self.leftLeg.knee.getRotationalLimitMotor(2)
        self.rightKneeZHinge = self.rightLeg.knee.getRotationalLimitMotor(2)
        self.leftKneeZHinge.setMotorEnabled(True)
        self.rightKneeZHinge.setMotorEnabled(True)
        self.leftKneeZHinge.setMaxMotorForce(200)
        self.rightKneeZHinge.setMaxMotorForce(200)
        self.leftKneeZHinge.setMaxLimitForce(400)
        self.rightKneeZHinge.setMaxLimitForce(400)
        self.leftLeg.knee.setAngularLimit(2, -180, 180)
        self.rightLeg.knee.setAngularLimit(2, -180, 180)


        self.leftArm = HumanoidArm(self.chest, self.world, self.armHeight, self.chestWidth/3-0.01, (self.chestWidth/3-0.01)*self.armHeight, False, startPosition, startHeading)

        frameA = TransformState.makePosHpr(Point3(-self.chestWidth/2-self.leftArm.upperArmDiameter/2, 0, self.chestHeight/2-self.leftArm.upperArmDiameter/8), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.leftArm.upperArmLength/2), Vec3(0, -90, 0))

        self.leftArmConstraint = BulletGenericConstraint(self.chest.node(), self.leftArm.upperArm.node(), frameA, frameB, True)
        self.leftArmConstraint.setDebugDrawSize(0.5)
        self.leftArmConstraint.setAngularLimit(0, -95, 135) # Front and back
        self.leftArmConstraint.setAngularLimit(1, 0, 0)     # Rotation, handled in the elbow joint because here it glitches.
        self.leftArmConstraint.setAngularLimit(2, -120, 35) # Left and right
        self.leftArm.upperArm.node().setAngularFactor(Vec3(0.2,0.2,0.2))
        self.world.attachConstraint(self.leftArmConstraint, linked_collision=True)


        self.rightArm = HumanoidArm(self.render, self.world, self.armHeight, self.chestWidth/3-0.01, (self.chestWidth/3-0.01)*self.armHeight, True, startPosition, startHeading)

        frameA = TransformState.makePosHpr(Point3(self.chestWidth/2+self.rightArm.upperArmDiameter/2, 0, self.chestHeight/2-self.rightArm.upperArmDiameter/8), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.rightArm.upperArmLength/2), Vec3(0, -90, 0))

        self.rightArmConstraint = BulletGenericConstraint(self.chest.node(), self.rightArm.upperArm.node(), frameA, frameB, True)
        self.rightArmConstraint.setDebugDrawSize(0.5)
        self.rightArmConstraint.setAngularLimit(0, -95, 135) # Front and back
        self.rightArmConstraint.setAngularLimit(1, 0, 0)     # Rotation, handled in the elbow joint because here it glitches.
        self.rightArmConstraint.setAngularLimit(2, -35, 120) # Left and right
        self.rightArm.upperArm.node().setAngularFactor(Vec3(0.2,0.2,0.2))
        self.world.attachConstraint(self.rightArmConstraint, linked_collision=True)


        self.head = createSphere(self.render, self.headHeight)
        self.head.node().setMass(3.0)
        self.head.setCollideMask(BitMask32.bit(3))
        self.world.attach(self.head.node())

        frameA = TransformState.makePosHpr(Point3(0,0,self.headHeight/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0,0,-self.chestHeight/2), Vec3(0, 0, 0))

        self.neck = BulletGenericConstraint(self.chest.node(), self.head.node(), frameA, frameB, True)

        self.neck.setDebugDrawSize(0.5)
        self.neck.setAngularLimit(0, -10, 10)
        self.neck.setAngularLimit(1, 0, 0)
        self.neck.setAngularLimit(2, -10, 10)
        self.world.attachConstraint(self.neck, linked_collision=True)

        self.head.setPosHpr(startPosition, startHeading)
        self.lowerTorso.setPosHpr(startPosition, startHeading)
        self.chest.setPosHpr(startPosition, startHeading)
        self.desiredHeading = self.lowerTorso.getH()


    # Set the humanoid's position on the Z axis.
    # newZ: the new Z position for the bottom of the feet
    def setPosZ(self, newZ):
        self.leftLeg.setZ(newZ)
        thighZ = self.rightLeg.setZ(newZ)
        self.lowerTorso.setZ(thighZ+self.lowerTorsoHeight/2)
        self.chest.setZ(thighZ+self.lowerTorsoHeight+self.chestHeight/2)
        self.head.setZ(thighZ+self.lowerTorsoHeight+self.chestHeight+self.headHeight/2)


    # A really hacky physics-driven movement implementation.
    # seconds: roughly how long each step should take in seconds
    # angle: angle in which to walk. For instance, zero is ahead, -90 is left and 90 is right.
    def takeStep(self, seconds, angle):
#        moveMass = self.leftLeg.foot.node().getMass()
        dt = globalClock.getDt()
        moveMass = 11+90*pow(dt, 0.7)
        self.updateHeading()
        
        if self.lastStepTime == 0:
            self.lastStepTime = time.time()
            timeDiff = 0
            timeDiff2Pi = 0
            self.leftLegConstraint.setAngularLimit(0, -self.legYLimit, self.legYLimit)
            self.rightLegConstraint.setAngularLimit(0, -self.legYLimit, self.legYLimit)
#            self.rightLeg.foot.node().setMass(moveMass)
        else:
            timeDiff = (time.time()-self.lastStepTime)/seconds
            timeDiff2Pi = 2*pi*timeDiff

        if abs(angleDiff(degrees(self.leftLegConstraint.getAngle(2)),angle)) > 90:
            self.inverted = True
            angle -= 180
            leftLegAngleError = angleDiff(degrees(self.leftLegConstraint.getAngle(2)),angle)
        else:
            self.inverted = False

        # A way to support an arbitrary walking angle
        self.leftLegZHinge.setTargetVelocity(angleDiff(degrees(self.leftLegConstraint.getAngle(2)),angle)/5)
        self.rightLegZHinge.setTargetVelocity(angleDiff(degrees(self.rightLegConstraint.getAngle(2)),angle)/5)
        self.leftKneeZHinge.setTargetVelocity(angleDiff(degrees(self.leftLeg.knee.getAngle(2)),-angle)/5)
        self.rightKneeZHinge.setTargetVelocity(angleDiff(degrees(self.rightLeg.knee.getAngle(2)),-angle)/5)
        
        #self.leftHeelYHinge.setTargetVelocity(radians(self.leftLeg.foot.getP())*4)
        #self.rightHeelYHinge.setTargetVelocity(radians(self.rightLeg.foot.getP())*4)

        #Enable ragdoll physics for the knee
        self.leftKneeYHinge.setMotorEnabled(False)
        self.rightKneeYHinge.setMotorEnabled(False)

        
        if (not self.inverted and self.leftLegConstraint.getAngle(0) <= self.rightLegConstraint.getAngle(0)) or self.inverted and self.leftLegConstraint.getAngle(0) > self.rightLegConstraint.getAngle(0):
            self.leftLeg.lowerLeg.node().setMass(moveMass)
            self.rightLeg.lowerLeg.node().setMass(5)
        else:
            self.rightLeg.lowerLeg.node().setMass(moveMass)
            self.leftLeg.lowerLeg.node().setMass(5)
        
        if (not self.inverted and self.leftLegConstraint.getAngle(0) <= self.rightLegConstraint.getAngle(0)) or self.inverted and self.leftLegConstraint.getAngle(0) > self.rightLegConstraint.getAngle(0):
            self.leftLeg.lowerLeg.node().setFriction(1.0)
            self.rightLeg.lowerLeg.node().setFriction(0.0)
        else:
            self.leftLeg.lowerLeg.node().setFriction(0.0)
            self.rightLeg.lowerLeg.node().setFriction(1.0)

        #velocity = self.lowerTorso.node().getLinearVelocity()
#        self.lowerTorso.setZ(abs(cos(timeDiff2Pi))*self.legHeight)
#        maxZ = getGroundZPos(self.lowerTorso, 9000, self.world, self.terrainBulletNode)+self.lowerTorsoHeight/2+abs(cos(timeDiff2Pi))*self.legHeight
#        self.lowerTorso.node().applyCentralImpulse(Vec3(0,0,10*(maxZ-self.lowerTorso.getZ())*abs((maxZ-self.lowerTorso.getZ()))))
#        velocity = cos(timeDiff2Pi)*self.legYLimit/seconds
        velocity = copysign((1-pow(1-abs(cos(timeDiff2Pi)), 0.2))*self.legYLimit/seconds, cos(timeDiff2Pi))
#        velocity = 10*cos(timeDiff2Pi)*self.legYLimit/seconds
        if self.inverted:
            velocity = -velocity
#        direction = radians(self.lowerTorso.getH())
        direction = radians(self.leftLeg.thigh.getH())
#        if not self.inverted:
        '''
        if self.leftLeg.foot.node().getMass() > moveMass - 0.1:
            self.rightLeg.thigh.node().applyTorque(Vec3(0.5*cos(timeDiff2Pi)*self.legYLimit/seconds,0,0))
            self.leftLeg.thigh.node().applyTorque(Vec3(-0.5*cos(timeDiff2Pi)*self.legYLimit/seconds,0,0))
        else:
            self.leftLeg.thigh.node().applyTorque(Vec3(0.5*cos(timeDiff2Pi)*self.legYLimit/seconds,0,0))
            self.rightLeg.thigh.node().applyTorque(Vec3(-0.5*cos(timeDiff2Pi)*self.legYLimit/seconds,0,0))
        '''
        '''
        force = 500/seconds
        if self.leftLeg.thigh.getP() < cos(timeDiff2Pi)*self.legYLimit:
            self.leftLeg.thigh.node().applyTorque(Vec3(force,0,0))
            self.rightLeg.thigh.node().applyTorque(Vec3(-force,0,0))
        else:
            self.rightLeg.thigh.node().applyTorque(Vec3(force,0,0))
            self.leftLeg.thigh.node().applyTorque(Vec3(-force,0,0))
        '''
        self.leftLeg.thigh.node().setAngularVelocity(Vec3(cos(direction)*velocity,sin(direction)*velocity,0))
        self.rightLeg.thigh.node().setAngularVelocity(Vec3(-cos(direction)*velocity,-sin(direction)*velocity,0))
#        if self.leftLeg.thigh.getP()*self.rightLeg.thigh.getP() >= 100:
#        self.leftLeg.lowerLeg.node().applyCentralImpulse(Vec3(sin(direction)*velocity*dt,0,-cos(direction)*velocity*dt))
#        self.rightLeg.lowerLeg.node().applyCentralImpulse(Vec3(-sin(direction)*velocity*dt,0,cos(direction)*velocity*dt))
#            self.leftLeg.thigh.node().setAngularVelocity(Vec3(velocity,0,0))
#            self.rightLeg.thigh.node().setAngularVelocity(Vec3(-velocity,0,0))
#            self.rightLeg.thigh.setP(-cos(timeDiff2Pi)*self.legYLimit)
#            self.leftLegConstraint.setAngularLimit(0, cos(timeDiff2Pi)*self.legYLimit, cos(timeDiff2Pi)*self.legYLimit)
#            self.leftLeg.foot.setY(self.lowerTorso.getY()+sin(cos(timeDiff2Pi)*self.legYLimit)*self.legHeight)
#            self.leftLeg.thigh.setX(self.lowerTorso.getX()+(self.pelvisWidth/2-0.01))
#            self.leftLegYHinge.setTargetVelocity(radians(self.legYLimit)+cos(timeDiff2Pi)*self.legYLimit/seconds)
#            self.rightLegYHinge.setTargetVelocity(-radians(self.legYLimit)-cos(timeDiff2Pi)*self.legYLimit/seconds)
#            self.lowerTorso.getH()
#            speed = 200
#            if self.rightLeg.foot.node().getMass() == 0:
#                self.leftLeg.foot.node().applyCentralForce(Vec3(speed/seconds*sin(self.leftLegConstraint.getAngle(2)),speed/seconds*cos(self.leftLegConstraint.getAngle(2)),0))
#            else:
#                self.rightLeg.foot.node().applyCentralForce(Vec3(speed/seconds*sin(self.rightLegConstraint.getAngle(2)),speed/seconds*cos(self.rightLegConstraint.getAngle(2)),0))
#        else:
#            pass
#            self.leftLegYHinge.setTargetVelocity(-cos(timeDiff2Pi)*radians(120)/seconds)
#            self.rightLegYHinge.setTargetVelocity(cos(timeDiff2Pi)*radians(120)/seconds)

        wantedHeight = self.legHeight+self.lowerTorsoHeight/2+getObjectGroundZPos(self.lowerTorso, self.world, self.terrainBulletNode)+9.81*dt
        if self.lowerTorso.getZ() < wantedHeight:
            self.lowerTorso.node().applyCentralImpulse(Vec3(0,0,300*dt+moveMass*2))
#        else:
#            self.lowerTorso.node().applyCentralImpulse(Vec3(0,0,-100*dt+moveMass))
#        if self.leftLeg.thigh.getP() >= 20:
#            self.leftLeg.lowerLeg.node().applyCentralImpulse(Vec3(0,0,-500*dt))
#        elif self.rightLeg.thigh.getP() >= 20:
#            self.rightLeg.lowerLeg.node().applyCentralImpulse(Vec3(0,0,-500*dt))
        '''
        if timeDiff >= seconds:
            self.lastStepTime = time.time()
            if self.leftLeg.foot.node().getMass() == 0:
                self.rightLeg.foot.node().setMass(moveMass)
                self.leftLeg.foot.node().setMass(1)
            else:
                self.leftLeg.foot.node().setMass(moveMass)
                self.rightLeg.foot.node().setMass(1)
        '''

    def standStill(self):
        dt = globalClock.getDt()
        if self.lastStepTime != 0:
            self.rightLeg.lowerLeg.node().setMass(5)
            self.leftLeg.lowerLeg.node().setMass(5)
            self.leftLeg.lowerLeg.node().setFriction(1.0)
            self.rightLeg.lowerLeg.node().setFriction(1.0)
            self.leftKneeYHinge.setMotorEnabled(True)
            self.rightKneeYHinge.setMotorEnabled(True)
            self.lastStepTime = 0
            self.leftLegConstraint.setAngularLimit(0, 0, 0)
            self.rightLegConstraint.setAngularLimit(0, 0, 0)

        #self.leftHeelYHinge.setTargetVelocity(radians(self.leftLeg.foot.getP())*6)
        #self.rightHeelYHinge.setTargetVelocity(radians(self.rightLeg.foot.getP())*6)

#        direction = radians(self.leftLeg.thigh.getH())
#        velocity = self.leftLegConstraint.getAngle(0)*40
#        self.leftLegYHinge.setTargetVelocity(-self.leftLegConstraint.getAngle(0)*4)
#        self.rightLegYHinge.setTargetVelocity(-self.rightLegConstraint.getAngle(0)*4)
#        self.leftLeg.thigh.node().setAngularVelocity(Vec3(cos(direction)*velocity,sin(direction)*velocity,0))
#        self.rightLeg.thigh.node().setAngularVelocity(Vec3(-cos(direction)*velocity,-sin(direction)*velocity,0))
        self.leftLegZHinge.setTargetVelocity(-self.leftLegConstraint.getAngle(2)*4)
        self.rightLegZHinge.setTargetVelocity(-self.rightLegConstraint.getAngle(2)*4)

        self.leftKneeYHinge.setTargetVelocity(-self.leftLeg.knee.getAngle(0)*8)
        self.rightKneeYHinge.setTargetVelocity(-self.rightLeg.knee.getAngle(0)*8)
        self.leftKneeZHinge.setTargetVelocity(-self.leftLeg.knee.getAngle(2)*4)
        self.rightKneeZHinge.setTargetVelocity(-self.rightLeg.knee.getAngle(2)*4)

        #self.setPosZ(getGroundZPos(self.lowerTorso, 9000, self.world, self.terrainBulletNode))
        #self.leftLeg.walkBlock.setPos(Vec3(self.leftLeg.foot.getX(), self.leftLeg.foot.getY(), getGroundZPos(self.leftLeg.foot, 9000, self.world, self.terrainBulletNode))-self.leftLeg.walkBlockOffset)
        #self.rightLeg.walkBlock.setPos(Vec3(self.rightLeg.foot.getX(), self.rightLeg.foot.getY(), getGroundZPos(self.rightLeg.foot, 9000, self.world, self.terrainBulletNode))-self.leftLeg.walkBlockOffset)

#        wantedHeight = self.legHeight+self.lowerTorsoHeight/2+getGroundZPos(self.lowerTorso, 9000, self.world, self.terrainBulletNode)+9.81*dt
#        if self.lowerTorso.getZ() < wantedHeight:
#            self.lowerTorso.node().applyCentralImpulse(Vec3(0,0,400*dt))

        self.updateHeading()
        
    def grabLeft(self, attachmentInfo):
        self.leftArm.grab(attachmentInfo)
        self.inLeftHand = attachmentInfo[0]

    def grabRight(self, attachmentInfo):
        self.rightArm.grab(attachmentInfo)
        self.inRightHand = attachmentInfo[0]

    def setLeftHandHpr(self, heading, pitch, roll):
        self.inLeftHand.setHpr(heading, pitch, roll)

    def setRightHandHpr(self, heading, pitch, roll):
        heading = heading + self.lowerTorso.getH()
        H = radians(heading+90)
        P = radians(pitch)
        x = cos(H) * cos(P)
        y = sin(H) * cos(P)
        z = sin(P)

        force = 10
        self.rightArm.forearm.node().applyCentralImpulse(Vec3(force*x,force*y,force*z))
        self.lowerTorso.node().applyCentralImpulse(Vec3(-force*x,-force*y,-force*z))
        self.inRightHand.setHpr(heading, pitch, roll)


    def turnLeft(self, dt):
        if abs(angleDiff(-self.lowerTorso.getH(), self.desiredHeading)) > 170:
            return
        self.desiredHeading -= dt*450
        self.desiredHeading = normalizeAngle(self.desiredHeading)
        self.updateHeading()

    def turnRight(self, dt):
        if abs(angleDiff(-self.lowerTorso.getH(), self.desiredHeading)) > 170:
            return
        self.desiredHeading += dt*450
        self.desiredHeading = normalizeAngle(self.desiredHeading)
        self.updateHeading()

    def updateHeading(self):
        diff = radians(angleDiff(-self.desiredHeading, self.lowerTorso.getH()))
        self.lowerTorso.node().setAngularVelocity(Vec3(0,0,-diff*8))
