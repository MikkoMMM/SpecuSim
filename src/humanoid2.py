import random
from src.InverseKinematics.IKChain import IKChain
from src.InverseKinematics.WalkCycle import WalkCycle
from src.InverseKinematics.Utils import *
from src.shapes import createPhysicsRoundedBox, createRoundedBox, createSphere
from src.humanoid_arm import HumanoidArm
from src.utils import angleDiff, normalizeAngle, getGroundZPos, getObjectGroundZPos
from math import cos, sin, radians, degrees
from panda3d.bullet import BulletSphereShape, BulletConeTwistConstraint, BulletGenericConstraint

class Humanoid():
    def __init__( self, render, world, terrainBulletNode, x, y, height=1.7, startHeading=Vec3(0,0,0), debug = False, debugTextNode = None ):
        self.render = render
        self.world = world
        self.terrainBulletNode = terrainBulletNode
        self.debug = debug

        # Initialize body proportions
        self.height = height
        self.headHeight = self.height/7
        self.chestWidth = 0.38
        self.pelvisWidth = 0.38
        self.lowerTorsoHeight = 1.5*(self.height/7)
        self.chestHeight = 1.5*(self.height/7)

        self.legHeight = self.height - self.headHeight - self.lowerTorsoHeight - self.chestHeight
        self.thighLength = self.legHeight*59/109
        thighDiameter = self.pelvisWidth/2-0.01
        self.lowerLegLength = self.legHeight*40/109
        lowerLegDiameter = (self.pelvisWidth/2-0.01)*self.legHeight
        self.footHeight = self.legHeight - self.thighLength - self.lowerLegLength
        self.footLength = lowerLegDiameter*2.2

        self.armHeight = self.legHeight*1
        self.upperArmLength = self.armHeight*50/100
        upperArmDiameter = self.chestWidth/3-0.01
        self.forearmLength = self.armHeight*50/100
        forearmDiameter = (self.chestWidth/3-0.01)*self.armHeight

        self.targetHeight = self.legHeight + self.lowerTorsoHeight/2

        # Control node and the whole body collision box
        self.lowerTorso = createRoundedBox(self.render, self.chestWidth, 0.2, self.chestHeight)
        startPosition = Vec3(x,y,self.targetHeight+getGroundZPos(x, y, self.world, self.terrainBulletNode))
        self.lowerTorso.setPosHpr(startPosition, startHeading)
        self.lowerTorso.node().setMass(70.0)
        self.lowerTorso.node().setAngularFactor(Vec3(0,0,0.1))
        self.lowerTorso.node().setLinearDamping(0.8)
        self.lowerTorso.node().setAngularSleepThreshold(0) # Sleep would freeze the whole character if still
        self.lowerTorso.setCollideMask(BitMask32.bit(3))
        self.world.attach(self.lowerTorso.node())

        self.chest = createRoundedBox(self.render, self.chestWidth, 0.2, self.chestHeight)
        self.chest.node().setMass(40.0)
        self.chest.node().setAngularFactor(Vec3(0.15,0.05,0.1))
        self.chest.node().setLinearDamping(0.5)
        self.chest.setCollideMask(BitMask32.bit(3))
        self.world.attach(self.chest.node())
        self.chest.node().setAngularSleepThreshold(0.05)

        frameA = TransformState.makePosHpr(Point3(0, 0, -self.chestHeight/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0, 0, self.lowerTorsoHeight/2), Vec3(0, 0, 0))

        swing1 = 10 # leaning forward/backward degrees
        swing2 = 5 # leaning side to side degrees
        twist = 30 # degrees

        cs = BulletConeTwistConstraint(self.chest.node(), self.lowerTorso.node(), frameA, frameB)
        cs.setDebugDrawSize(0.5)
        cs.setLimit(twist, swing2, swing1, softness=0.1, bias=1.0, relaxation=1.0)
        world.attachConstraint(cs, linked_collision=True)


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

        ##################################
        # Set up body movement:
        self.walkSpeed = 2  # m/s
        self.turnSpeed = 300


        # Set up information needed by inverse kinematics
        thigh = []
        lowerLeg = []
        self.foot = []
        self.leg = []
        self.footTarget = []
        self.plannedFootTarget = []

        for i in range(2):
            if i == 0:
                horizontalPlacement = -1
            else:
                horizontalPlacement = 1

            hip = self.lowerTorso.attachNewNode("Hip")
            hip.setPos(Vec3(horizontalPlacement*self.pelvisWidth/4,0,-self.lowerTorsoHeight/2))
            self.leg.append(IKChain( hip ))

            thigh.append(self.leg[i].addBone( offset=Vec3(0,0,-self.thighLength),
                    minAng = -math.pi*0.25,
                    maxAng = math.pi*0.25,
                    rotAxis = None,
                    ))

            lowerLeg.append(self.leg[i].addBone( offset=Vec3(0,0,-self.lowerLegLength),
                    minAng = -math.pi*0.5,
                    maxAng = 0,
                    rotAxis = LVector3f.unitX(),
                    parentBone = thigh[i]
                    ))

            self.leg[i].finalize()
            self.foot.append(lowerLeg[i].ikNode.attachNewNode("Foot"))
            self.foot[i].setPosHpr(Vec3(0,lowerLegDiameter/2,-self.lowerLegLength-self.footHeight/2), Vec3(0,0,0))

            if self.debug:
                self.leg[i].debugDisplay()


            #################################################
            # Foot targets:

            # Set up a target that the foot should reach:
            self.footTarget.append(self.render.attachNewNode("FootTarget"))
            self.footTarget[i].setZ(self.targetHeight+getObjectGroundZPos(self.footTarget[i], self.world, self.terrainBulletNode))
            self.leg[i].setTarget( self.footTarget[i] )

            # Set up nodes which stay (rigidly) infront of the body, on the floor.
            # Whenever a leg needs to take a step, the target will be placed on this position:
            self.plannedFootTarget.append(self.lowerTorso.attachNewNode( "PlannedFootTarget" ))
            stepDist = 0.15
            self.plannedFootTarget[i].setPos( horizontalPlacement*self.pelvisWidth/4, stepDist, -self.targetHeight )

            if self.debug:
                geom = createAxes( 0.2 )
                self.footTarget[i].attachNewNode( geom )
                self.plannedFootTarget[i].attachNewNode( geom )


        # Add visuals to the bones. These MUST be after finalize().

        for i in range(2):
            visual = loader.loadModel("models/unit_cylinder.bam")
            visual.setScale(Vec3(thighDiameter, thighDiameter, self.thighLength))
            visual.reparentTo(thigh[i].ikNode)
            visual.setPos( (visual.getPos() + thigh[i].offset)/2 )

            visual = loader.loadModel("models/unit_cylinder.bam")
            visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter, self.lowerLegLength))
            visual.reparentTo(lowerLeg[i].ikNode)
            visual.setPos( (visual.getPos() + lowerLeg[i].offset)/2 )

            footVisual = loader.loadModel("models/unit_cube.bam")
            footVisual.reparentTo(self.foot[i])
            footVisual.setScale(Vec3(lowerLegDiameter, self.footLength, self.footHeight))


        self.head.setPosHpr(startPosition, startHeading)
#        self.lowerTorso.setPosHpr(startPosition, startHeading)
        self.chest.setPosHpr(startPosition, startHeading)

        self.legMovementSpeed = self.walkSpeed*3

        self.stepLeft = False
        self.stepRight = False
        
        self.walkCycle = WalkCycle( 2, 0.75 )
        self.desiredHeading = self.lowerTorso.getH()


    def speedUp( self ):
        self.walkSpeed += 0.1
        self.walkSpeed = min(self.walkSpeed, 9)
        self.legMovementSpeed = self.walkSpeed*3

    def slowDown( self ):
        self.walkSpeed -= 0.1
        self.walkSpeed = max(self.walkSpeed, 0)
        self.legMovementSpeed = self.walkSpeed*3


    def getCorrectZVelocity(self, currentZPos=None):
        # Too high and you'll get massive jittering at sharp points in the terrain physics node
        vector = self.lowerTorso.node().getLinearVelocity()
        maxZChange = 4*globalClock.getDt()*min(self.walkSpeed, Vec3(vector.getX(), vector.getY(), 0).length())
        if currentZPos:
            return -min(maxZChange,max(currentZPos,-maxZChange))/globalClock.getDt()
        return -min(maxZChange,max(self.getFeetAveragedGroundZPos(),-maxZChange))/globalClock.getDt()


    def getFeetAveragedGroundZPos(self, offsetX=0, offsetY=0):
        averageX = 0
        averageY = 0
        averageZ = 0
        for foot in self.foot:
            averageX += foot.getX(self.render)
            averageY += foot.getY(self.render)
            averageZ += foot.getZ(self.render)-self.footHeight/2
        averageX /= len(self.foot)
        averageY /= len(self.foot)
        averageZ /= len(self.foot)
        averageZ -= getGroundZPos(averageX+offsetX, averageY+offsetY, self.world, self.terrainBulletNode)
        return averageZ


    def standStill(self):
        self.walkInDir(self.lowerTorso.getH(),decelerate=True)
        

    def walkInDir( self, angle=0, visuals=True, decelerate=False ):
        if not decelerate:
            mathAngle = radians(angle+90)
            diff = Vec3(-cos(mathAngle),sin(mathAngle),0)
            diffN = diff.normalized()
            step = diffN*self.walkSpeed

        currentZPos = self.getFeetAveragedGroundZPos()
        preliminaryZVelocity = self.getCorrectZVelocity(currentZPos)
        if decelerate:
            newVector = Vec3(self.lowerTorso.node().getLinearVelocity().getX(), self.lowerTorso.node().getLinearVelocity().getY(), preliminaryZVelocity)
        else:
            ca = cos(radians(self.lowerTorso.getH()))
            sa = sin(radians(self.lowerTorso.getH()))
            newVector = Vec3(ca*step.getX() - sa*step.getY(), sa*step.getX() + ca*step.getY(), preliminaryZVelocity)
        zDiff = currentZPos - self.getFeetAveragedGroundZPos(offsetX=newVector.getX()*0.01, offsetY=newVector.getY()*0.01)

        multMin = 0.01
        if zDiff > multMin:
            multMax = 0.02
            mult = ((1/multMax)*(multMax-multMin - (min(multMax,zDiff)-multMin)))
            self.lowerTorso.node().setLinearVelocity(Vec3(newVector.getX()*mult, newVector.getY()*mult, preliminaryZVelocity))
            if zDiff >= multMax:
                return
        else:
            self.lowerTorso.node().setLinearVelocity(newVector)

        # Negligible speed; assume we've come to a halt and save on resources
        if self.lowerTorso.node().getLinearVelocity().length() < 0.2 and abs(self.lowerTorso.node().getAngularVelocity().getZ()) < 0.1:
            self.lowerTorso.node().setLinearVelocity(Vec3(0,0,self.lowerTorso.node().getLinearVelocity().getZ()))
            return

        if visuals:
            # Calculate how far we've walked this frame:
            curWalkDist = self.lowerTorso.node().getLinearVelocity().length()*globalClock.getDt()
            self._walkingVisuals( curWalkDist, 0 )


    def _walkingVisuals( self, curWalkDist, angClamped ):
        #############################
        # Update legs:

        # Move planned foot target further forward (longer steps) when character is
        # walking faster:
        stepDist = curWalkDist*0.1/globalClock.getDt()
        left = 0
        right = 1
        self.plannedFootTarget[left].setPos( -self.pelvisWidth/4, stepDist, -self.targetHeight )
        self.plannedFootTarget[left].setZ( self.render, getGroundZPos(self.plannedFootTarget[left].getX(self.render), self.plannedFootTarget[left].getY(self.render), self.world, self.terrainBulletNode) )
        self.plannedFootTarget[right].setPos( self.pelvisWidth/4, stepDist, -self.targetHeight )
        self.plannedFootTarget[right].setZ( self.render, getGroundZPos(self.plannedFootTarget[right].getX(self.render), self.plannedFootTarget[right].getY(self.render), self.world, self.terrainBulletNode) )

        # Update the walkcycle to determine if a step needs to be taken:
        update = curWalkDist
        update += angClamped*0.5
        self.walkCycle.updateTime( update )

        if self.walkCycle.stepRequired[0]:
            self.walkCycle.step( 0 )
            self.stepLeft = True
        if self.walkCycle.stepRequired[1]:
            self.walkCycle.step( 1 )
            self.stepRight = True

        if self.stepLeft:
            diff = self.plannedFootTarget[left].getPos(self.render) - self.footTarget[left].getPos()
            legMoveDist = self.legMovementSpeed*globalClock.getDt()
            if diff.length() < legMoveDist:
                self.footTarget[left].setPos( self.plannedFootTarget[left].getPos( self.render ) )
                self.stepLeft = False
            else:
                moved = self.footTarget[left].getPos() + diff.normalized()*legMoveDist
                self.footTarget[left].setPos( moved )

        if self.stepRight:
            diff = self.plannedFootTarget[right].getPos(self.render) - self.footTarget[right].getPos()
            legMoveDist = self.legMovementSpeed*globalClock.getDt()
            if diff.length() < legMoveDist:
                self.footTarget[right].setPos( self.plannedFootTarget[right].getPos( self.render ) )
                self.stepRight = False
            else:
                moved = self.footTarget[right].getPos() + diff.normalized()*legMoveDist
                self.footTarget[right].setPos( moved )

        self.leg[left].updateIK()
        self.leg[right].updateIK()


    def turnLeft(self):
        if abs(angleDiff(-self.lowerTorso.getH(), self.desiredHeading)) > 170:
            return
        self.desiredHeading -= globalClock.getDt()*450
        self.desiredHeading = normalizeAngle(self.desiredHeading)
        self.updateHeading()

    def turnRight(self):
        if abs(angleDiff(-self.lowerTorso.getH(), self.desiredHeading)) > 170:
            return
        self.desiredHeading += globalClock.getDt()*450
        self.desiredHeading = normalizeAngle(self.desiredHeading)
        self.updateHeading()

    def updateHeading(self):
        diff = radians(angleDiff(-self.desiredHeading, self.lowerTorso.getH()))
        self.lowerTorso.node().setAngularVelocity(Vec3(0,0,-diff*8))
