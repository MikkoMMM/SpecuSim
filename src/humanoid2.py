import random
from src.InverseKinematics.IKChain import IKChain
from src.InverseKinematics.WalkCycle import WalkCycle
from src.InverseKinematics.Utils import *
from src.shapes import createPhysicsRoundedBox
from src.utils import angleDiff, normalizeAngle, getGroundZPos, getObjectGroundZPos
from math import cos, sin, radians, degrees

class Humanoid():
    def __init__( self, render, world, terrainBulletNode, x, y, height=1.7, debug = False ):
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
        self.lowerTorso = createPhysicsRoundedBox(self.render, self.chestWidth, 0.2, self.chestHeight)
        self.lowerTorso.setPos(Vec3(x,y,self.targetHeight+getGroundZPos(x, y, self.world, self.terrainBulletNode)))
        self.lowerTorso.node().setMass(70.0)
        self.lowerTorso.node().setAngularFactor(Vec3(0,0,0.1))
        self.lowerTorso.node().setLinearDamping(0.5)
        self.lowerTorso.node().setAngularSleepThreshold(0) # TODO: Test without, but on previous implementation, sleep seemed to freeze the whole character if still
        self.lowerTorso.setCollideMask(BitMask32.bit(3))
        self.world.attach(self.lowerTorso.node())
        self.lowerTorso.node().setGravity(Vec3(0,0,0))


        ##################################
        # Set up body movement:
        self.walkSpeed = 1  # m/s
        self.turnSpeed = 100


        # Set up information needed by inverse kinematics
        thigh = []
        lowerLeg = []
        self.foot = []
        self.leg = []
        self.footTarget = []
        self.plannedFootTarget = []

        for i in range(2):
            self.leg.append(IKChain( self.lowerTorso ))

            if i == 0:
                horizontalPlacement = -1
            else:
                horizontalPlacement = 1

            hip = self.leg[i].addBone( offset=Vec3(horizontalPlacement*self.pelvisWidth/4,0,-self.lowerTorsoHeight/2),
                    minAng = 0,
                    maxAng = 0,
                    rotAxis = None,
                    )

            thigh.append(self.leg[i].addBone( offset=Vec3(0,0,-self.thighLength),
                    minAng = -math.pi*0.25,
                    maxAng = math.pi*0.25,
                    rotAxis = None,
                    parentBone = hip
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
            geom = createAxes( 0.1 )
            self.footTarget[i].attachNewNode( geom )
            self.footTarget[i].setZ(self.targetHeight+getObjectGroundZPos(self.footTarget[i], self.world, self.terrainBulletNode))
            self.leg[i].setTarget( self.footTarget[i] )

            # Set up nodes which stay (rigidly) infront of the body, on the floor.
            # Whenever a leg needs to take a step, the target will be placed on this position:
            self.plannedFootTarget.append(self.lowerTorso.attachNewNode( "PlannedFootTarget" ))
            stepDist = 0.15
            self.plannedFootTarget[i].setPos( horizontalPlacement*self.pelvisWidth/4, stepDist, -self.targetHeight )
            self.plannedFootTarget[i].attachNewNode( geom )


        # Add visuals to the bones. These MUST be after finalize().
        lowerTorsoVisual = loader.loadModel("models/unit_cylinder.bam")
        lowerTorsoVisual.setScale(Vec3(self.chestWidth, 0.2, self.lowerTorsoHeight))
        lowerTorsoVisual.reparentTo(self.lowerTorso)


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
#            footVisual.setPosHpr(Vec3(0,lowerLegDiameter*2,-self.lowerLegLength*2-self.footHeight), Vec3(0,0,0))
#            visual.clearModelNodes()
#            footVisual.clearModelNodes()
#            visual.flattenStrong()
#            footVisual.flattenStrong()


        self.legMovementSpeed = self.walkSpeed*3

        self.stepLeft = False
        self.stepRight = False
        
        self.walkCycle = WalkCycle( 2, 0.75 )
        self.desiredHeading = self.lowerTorso.getH()


    def getCorrectZVelocity(self):
        lowestFootZ = 9999
        # Too high and you'll get massive jittering at sharp points in the terrain physics node
        maxZChange = 4*globalClock.getDt()
        average = 0
        for foot in self.foot:
            average += foot.getZ(self.render)-getGroundZPos(foot.getX(self.render), foot.getY(self.render), self.world, self.terrainBulletNode)
        return -min(maxZChange,max(average/len(self.foot),-maxZChange))/globalClock.getDt()


    def walkInDir( self, angle=0, strafe=True, visuals=True ):
        mathAngle = radians(angle+90)
        diff = Vec3(-cos(mathAngle),sin(mathAngle),0)
        diffN = diff.normalized()
        maxRot = self.turnSpeed*globalClock.getDt()

        step = diffN*self.walkSpeed
        step.setZ(self.getCorrectZVelocity())
        if strafe:
            ca = cos(radians(self.lowerTorso.getH()))
            sa = sin(radians(self.lowerTorso.getH()))
            self.lowerTorso.node().setLinearVelocity(Vec3(ca*step.getX() - sa*step.getY(), sa*step.getX() + ca*step.getY(), step.getZ()))

            # Calculate how far we've walked this frame:
            curWalkDist = step.length()*globalClock.getDt()

            if visuals:
                self._walkingVisuals( curWalkDist, 0 )
        else:
            self.desiredHeading = normalizeAngle(angle)
            self.updateHeading()
            if abs( angleDiff(-self.desiredHeading, self.lowerTorso.getH()) ) < maxRot:
                self.lowerTorso.node().setLinearVelocity(step)

                # Calculate how far we've walked this frame:
                curWalkDist = step.length()*globalClock.getDt()

                if visuals:
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
