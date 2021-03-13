from panda3d.core import *
import random, math
from src.InverseKinematics.IKChain import IKChain
from src.InverseKinematics.WalkCycle import WalkCycle
from src.InverseKinematics.Utils import *
from src.shapes import createPhysicsRoundedBox

class Humanoid():
    def __init__( self, render, world, x, y, height=1.7, debug = False ):

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

        # Control node and the whole body collision box
        self.lowerTorso = createPhysicsRoundedBox(render, self.chestWidth, 0.2, self.chestHeight)
        self.lowerTorso.setX(x)
        self.lowerTorso.setY(y)
        self.lowerTorso.node().setMass(70.0)
        self.lowerTorso.node().setAngularFactor(Vec3(0,0,0.1))
        self.lowerTorso.node().setLinearDamping(0.5)
        self.lowerTorso.node().setAngularSleepThreshold(0) # For whatever reason, sleep seems to freeze the whole character if still
        self.lowerTorso.setCollideMask(BitMask32.bit(3))
        world.attach(self.lowerTorso.node())
        self.lowerTorso.node().setGravity(Vec3(0,0,0))


        ##################################
        # Set up body movement:

        self.targetNode = render.attachNewNode( "WalkTarget" )
        geom = createAxes( 0.2 )
        self.targetNode.attachNewNode( geom )
        self.walkSpeed = 1  # m/s
        self.turnSpeed = 2
        self.newRandomTarget()


        # Set up information needed by inverse kinematics
        thigh = []
        lowerLeg = []
        self.leg = []
        self.footTarget = []
        self.plannedFootTarget = []
        self.targetHeight = -self.legHeight - self.lowerTorsoHeight/2

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
            if debug:
                self.leg[i].debugDisplay()


            #################################################
            # Foot targets:

            # Set up a target that the foot should reach:
            self.footTarget.append(render.attachNewNode("FootTarget"))
            geom = createAxes( 0.1 )
            self.footTarget[i].attachNewNode( geom )
            self.leg[i].setTarget( self.footTarget[i] )

            # Set up nodes which stay (rigidly) infront of the body, on the floor.
            # Whenever a leg needs to take a step, the target will be placed on this position:
            self.plannedFootTarget.append(self.lowerTorso.attachNewNode( "PlannedFootTarget" ))
            stepDist = 0.15
            self.plannedFootTarget[i].setPos( horizontalPlacement*0.15, stepDist, self.targetHeight )
            self.plannedFootTarget[i].attachNewNode( geom )


        # Add visuals to the bones. These MUST be after finalize().
        lowerTorsoVisual = loader.loadModel("models/unit_cylinder.bam")
        lowerTorsoVisual.setScale(Vec3(self.chestWidth, 0.2, self.lowerTorsoHeight))
        lowerTorsoVisual.reparentTo(self.lowerTorso)
#        lowerTorsoVisual.setPos( (lowerTorsoVisual.getPos() + self.lowerTorsoHeight)/2 )


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
            footVisual.reparentTo(visual)
            # I'm not exactly sure why it needs such weird scaling
            footVisual.setScale(Vec3(lowerLegDiameter*6, self.footLength*6, self.footHeight*3.5))
            footVisual.setPosHpr(Vec3(0,lowerLegDiameter*2,-self.lowerLegLength*2-self.footHeight), Vec3(0,0,0))
#            visual.clearModelNodes()
#            footVisual.clearModelNodes()
#            visual.flattenStrong()
#            footVisual.flattenStrong()


        self.legMovementSpeed = self.walkSpeed*3

        self.stepLeft = False
        self.stepRight = False
        
        self.walkCycle = WalkCycle( 2, 0.75 )

    '''
    def moveTarget( self, task ):
        ikChain = self.leg[0]
        ikChain.target.setPos( 2.5*math.sin(task.time), 5*math.sin(task.time*1.6+2), math.cos(task.time*1.6+2) )
        ikChain.updateIK()

        ikChain = self.leg[1]
        ikChain.target.setPos( -2.5*math.sin(task.time), -5*math.sin(task.time*1.6+2), math.cos(task.time*1.6+2) )
        ikChain.updateIK()

#        self.lowerTorso.node().applyCentralForce(Vec3(0,self.lowerTorso.node().getMass()*4.0,0))
        return task.cont
    '''

    def walk( self, task ):

        #############################
        # Update body:

        prevPos = self.lowerTorso.getPos()

        diff = self.targetNode.getPos( self.lowerTorso )
        diff.z = 0
        diffN = diff.normalized()
        ang = LVector3f.unitY().angleRad( diffN )
        axis = LVector3f.unitY().cross( diffN )
        axis.normalize()
        maxRot = self.turnSpeed*globalClock.getDt()
        angClamped = 0
        if axis.length() > 0.999:
            # Limit angle:
            angClamped = max( -maxRot, min( maxRot, ang ) )
            q = Quat()
            q.setFromAxisAngleRad( angClamped, axis )

            qOld = self.lowerTorso.getQuat()
            qNew = q*qOld
            self.lowerTorso.setQuat( qNew  )
        if abs( ang ) < maxRot:
            step = diffN*self.walkSpeed*globalClock.getDt()
            if step.lengthSquared() > diff.lengthSquared():
                self.newRandomTarget()
                step = diff
            step = self.lowerTorso.getQuat().xform( step )
            self.lowerTorso.setPos( self.lowerTorso.getPos() + step )

        # Calculate how far we've walked this frame:
        curWalkDist = (prevPos - self.lowerTorso.getPos()).length()

        #############################
        # Update legs:

        # Move planned foot target further forward (longer steps) when character is
        # walking faster:
        stepDist = curWalkDist*0.1/globalClock.dt
        left = 0
        right = 1
        self.plannedFootTarget[left].setPos( -0.15, stepDist, self.targetHeight )
        self.plannedFootTarget[right].setPos( 0.15, stepDist, self.targetHeight )

        # Update the walkcycle to determine if a step needs to be taken:
        #update = curWalkDist*0.1/globalClock.dt
        update = curWalkDist
        update += angClamped*0.5
        self.walkCycle.updateTime( update )

        if self.walkCycle.stepRequired[0]:
            #self.footTargetLeft.setPos( self.plannedFootTargetLeft.getPos( render ) )
            self.walkCycle.step( 0 )
            self.stepLeft = True
        if self.walkCycle.stepRequired[1]:
            #self.footTargetRight.setPos( self.plannedFootTargetRight.getPos( render ) )
            self.walkCycle.step( 1 )
            self.stepRight = True

        if self.stepLeft:
            diff = self.plannedFootTarget[left].getPos(render) - self.footTarget[left].getPos()
            legMoveDist = self.legMovementSpeed*globalClock.dt
            if diff.length() < legMoveDist:
                self.footTarget[left].setPos( self.plannedFootTarget[left].getPos( render ) )
                self.stepLeft = False
            else:
                moved = self.footTarget[left].getPos() + diff.normalized()*legMoveDist
                self.footTarget[left].setPos( moved )

        if self.stepRight:
            diff = self.plannedFootTarget[right].getPos(render) - self.footTarget[right].getPos()
            legMoveDist = self.legMovementSpeed*globalClock.dt
            if diff.length() < legMoveDist:
                self.footTarget[right].setPos( self.plannedFootTarget[right].getPos( render ) )
                self.stepRight = False
            else:
                moved = self.footTarget[right].getPos() + diff.normalized()*legMoveDist
                self.footTarget[right].setPos( moved )

        self.leg[left].updateIK()
        self.leg[right].updateIK()

        return task.cont

    
    def newRandomTarget( self ):

        self.targetNode.setPos(
                LVector3f( random.random()*10-5,
                    random.random()*10-5,
                    0 ) )
