from panda3d.core import *
import random, math
from src.InverseKinematics.IKChain import IKChain
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
        self.body = createPhysicsRoundedBox(render, self.chestWidth, 0.2, self.chestHeight)
        self.body.setX(x)
        self.body.setY(y)
        self.body.node().setMass(70.0)
        self.body.node().setAngularFactor(Vec3(0,0,0.1))
        self.body.node().setLinearDamping(0.5)
        self.body.node().setAngularSleepThreshold(0) # For whatever reason, sleep seems to freeze the whole character if still
        self.body.setCollideMask(BitMask32.bit(3))
        world.attach(self.body.node())
        self.body.node().setGravity(Vec3(0,0,0))
        '''
        lines = LineSegs()
        if debug:
            col = (random.random(), random.random(), random.random())
            lines.setThickness(15)
            lines.setColor( col[0], col[1], col[2] )
        lines.moveTo(0, 0, 0)
        
        self.body = render.attachNewNode(lines.create())
        self.body.setPos( 0,0,0 )
        '''

        # Set up information needed by inverse kinematics
        self.torso = IKChain( self.body )

        self.lowerTorso = self.torso.addBone( offset=Vec3(0,0,-self.lowerTorsoHeight),
                minAng = 0,
                maxAng = 0,
                rotAxis = None
                )

        self.torso.finalize()

        thigh = []
        lowerLeg = []
        self.leg = []

        for i in range(2):
            self.leg.append(IKChain( self.body ))

            if i == 0:
                horizontalPlacement = -1
            else:
                horizontalPlacement = 1

#            hip = self.leg[-1].addBone( offset=Vec3(0,horizontalPlacement*self.pelvisWidth/4,0),
#                    minAng = math.pi*0.5,
#                    maxAng = math.pi*0.5,
            hip = self.leg[-1].addBone( offset=Vec3(horizontalPlacement*self.pelvisWidth/4,0,-self.lowerTorsoHeight),
                    minAng = 0,
                    maxAng = 0,
                    rotAxis = None,
                    )

            thigh.append(self.leg[-1].addBone( offset=Vec3(0,0,-self.thighLength),
                    minAng = -math.pi*0.25,
                    maxAng = math.pi*0.25,
                    rotAxis = None,
                    parentBone = hip
                    ))

            lowerLeg.append(self.leg[-1].addBone( offset=Vec3(0,0,-self.lowerLegLength),
                    minAng = -math.pi*0.5,
                    maxAng = 0,
                    rotAxis = LVector3f.unitX(),
                    parentBone = thigh[-1]
                    ))
            self.leg[-1].finalize()


        # Add visuals to the bones. These MUST be after finalize().
        lowerTorsoVisual = loader.loadModel("models/unit_cylinder.bam")
        lowerTorsoVisual.setScale(Vec3(self.chestWidth, 0.2, self.lowerTorsoHeight))
        lowerTorsoVisual.reparentTo(self.lowerTorso.ikNode)
        lowerTorsoVisual.setPos( (lowerTorsoVisual.getPos() + self.lowerTorso.offset)/2 )


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
            self.leg[i].animateTarget = True

            ##################################
            ## Target point:
            lines = LineSegs()
            if debug:
                col = (random.random(), random.random(), random.random())
                lines.setThickness(15)
                lines.setColor( col[0], col[1], col[2] )
            lines.moveTo(0, 0, 0)
            
            target = render.attachNewNode(lines.create())
            target.reparentTo(self.body)
            target.setPos( 2,0,2 )

            self.leg[i].setTarget( target )



        if debug:
            self.torso.debugDisplay()
            for i in range(2):
                self.leg[i].debugDisplay()


    def moveTarget( self, task ):
        ikChain = self.leg[0]
        ikChain.target.setPos( 2.5*math.sin(task.time), 5*math.sin(task.time*1.6+2), math.cos(task.time*1.6+2) )
        ikChain.updateIK()

        ikChain = self.leg[1]
        ikChain.target.setPos( -2.5*math.sin(task.time), -5*math.sin(task.time*1.6+2), math.cos(task.time*1.6+2) )
        ikChain.updateIK()

        self.body.node().applyCentralForce(Vec3(0,self.body.node().getMass()*4.0,0))
        return task.cont
