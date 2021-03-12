from panda3d.core import *
import random, math
from src.InverseKinematics.IKCharacter import IKCharacter

class Humanoid():
    def __init__( self, parent, x, y, debug = False ):
        self.char = IKCharacter( parent )

        self.thighLength = 59/109
        self.lowerLegLength = 40/109

        thigh = self.char.addBone( offset=Vec3(0,0,-self.thighLength),
                minAng = -math.pi*0.2,
                maxAng = math.pi*0.2,
                rotAxis = None
                )

        lowerLeg = self.char.addBone( offset=Vec3(0,0,-self.lowerLegLength),
                minAng = -math.pi*0.5,
                maxAng = 0,
                rotAxis = LVector3f.unitX(),
                parentBone = thigh
                )
        self.char.finalize(x,y)

        # Add visuals to the bones. These MUST be after finalize().
        visual = loader.loadModel("models/unit_cylinder.bam")
        lowerLegDiameter = 0.2
        visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter, self.thighLength))
        visual.reparentTo(thigh.ikNode)
        visual.setPos( (visual.getPos() + thigh.offset)/2 )

        visual = loader.loadModel("models/unit_cylinder.bam")
        lowerLegDiameter = 0.15
        visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter, self.lowerLegLength))
        visual.reparentTo(lowerLeg.ikNode)
        visual.setPos( (visual.getPos() + lowerLeg.offset)/2 )

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
        #lines.drawTo(np.getPos(parentNode))
        #point = render.attachNewNode("Point")
        self.char.ikTarget = render.attachNewNode(lines.create())
        self.char.ikTarget.setPos( 2,0,2 )
        

        self.char.setTarget( self.char.ikTarget )


    def moveTarget( self, task ):
        if self.char.animateTarget:
            self.char.ikTarget.setPos( 2.5*math.sin(task.time), 5*math.sin(task.time*1.6+2), math.cos(task.time*1.6+2) )

        self.char.updateIK()
        return task.cont
