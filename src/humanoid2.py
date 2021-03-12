from panda3d.core import *
import random, math
from src.InverseKinematics.IKCharacter import IKCharacter

class Humanoid():
    def __init__( self, parent, x, y, height=1.7, debug = False ):

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


        # Set up information needed by inverse kinematics
        self.char = IKCharacter( parent )

        self.lowerTorso = self.char.addBone( offset=Vec3(0,0,-self.lowerTorsoHeight),
                minAng = 0,
                maxAng = 0,
                rotAxis = None
                )

        left = 0
        right = 1
        thigh = []
        lowerLeg = []

        for i in range(2):
            if i == 0:
                horizontalPlacement = -1
            else:
                horizontalPlacement = 1

            hip = self.char.addBone( offset=Vec3(horizontalPlacement*self.pelvisWidth/4,0,0),
                    minAng = 0,
                    maxAng = 0,
                    rotAxis = None,
                    parentBone = self.lowerTorso
                    )

            thigh.append(self.char.addBone( offset=Vec3(0,0,-self.thighLength),
                    minAng = -math.pi*0.25,
                    maxAng = math.pi*0.25,
                    rotAxis = None,
                    parentBone = hip
                    ))

            lowerLeg.append(self.char.addBone( offset=Vec3(0,0,-self.lowerLegLength),
                    minAng = -math.pi*0.5,
                    maxAng = 0,
                    rotAxis = LVector3f.unitX(),
                    parentBone = thigh[-1]
                    ))

        self.char.finalize(x,y)

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
        


        if debug:
            self.char.debugDisplay()


        self.char.animateTarget = True

        ##################################
        ## Target point:
        col = (random.random(), random.random(), random.random())

        lines = LineSegs()
        lines.setThickness(15)
        lines.setColor( col[0], col[1], col[2] )
        lines.moveTo(0, 0, 0)
        self.char.ikTarget = render.attachNewNode(lines.create())
        self.char.ikTarget.setPos( 2,0,2 )

        self.char.setTarget( self.char.ikTarget )


    def moveTarget( self, task ):
        if self.char.animateTarget:
            self.char.ikTarget.setPos( 2.5*math.sin(task.time), 5*math.sin(task.time*1.6+2), math.cos(task.time*1.6+2) )

        self.char.updateIK()

#        dt = globalClock.getDt()
        return task.cont
