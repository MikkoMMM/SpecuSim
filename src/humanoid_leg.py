from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import ZUp
from src.shapes import createCapsule, createPhysicsSphere
from math import cos, sin, radians, asin

class HumanoidLeg():
    # Arguments:
    # render: NodePath to render to
    # world: A BulletWorld to use for physics
    # height: leg's total height
    # thighDiameter: thigh's diameter
    # lowerLegDiameter: lower leg's diameter
    def __init__(self, render, world, height, thighDiameter, lowerLegDiameter, startPosition, startHeading):
        self.render = render
        self.world = world

        axisA = Vec3(1, 0, 0)
        self.thighLength = height*59/109
        self.lowerLegLength = height*40/109
        self.footHeight = height - self.thighLength - self.lowerLegLength
        self.footLength = lowerLegDiameter*2.2

        self.thigh = createCapsule(self.render, thighDiameter, self.thighLength)
        self.thigh.node().setMass(10.0)
        self.world.attach(self.thigh.node())


        # The lower legs are special in that they collide with the ground and their physics boxes are larger than the visuals
        self.lowerLeg = createPhysicsSphere(self.render, self.lowerLegLength+self.footHeight*3)
        self.lowerLeg.node().setMass(5.0)
        self.world.attach(self.lowerLeg.node())
        lowerLegVisual = loader.loadModel("models/unit_cylinder.bam")
        lowerLegVisual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter, self.lowerLegLength))
        lowerLegVisual.reparentTo(self.lowerLeg)
        self.lowerLeg.setCollideMask(BitMask32.bit(2)) # Collides with ground

        frameA = TransformState.makePosHpr(Point3(0,0,-self.thighLength/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0,0,self.lowerLegLength/2), Vec3(0, 0, 0))

        self.knee = BulletGenericConstraint(self.thigh.node(), self.lowerLeg.node(), frameA, frameB, True)

        self.knee.setDebugDrawSize(0.5)
        self.knee.setAngularLimit(0, 0, 45)
        self.knee.setAngularLimit(1, 0, 0)
        self.knee.setAngularLimit(2, 0, 0)
        self.world.attachConstraint(self.knee, linked_collision=True)


        footVisual = loader.loadModel("models/unit_cube.bam")
        footVisual.reparentTo(lowerLegVisual)
        # I'm not exactly sure why it needs such weird scaling
        footVisual.setScale(Vec3(lowerLegDiameter*6, self.footLength*6, self.footHeight*3.5))
        footVisual.setPosHpr(Vec3(0,lowerLegDiameter*2,-self.lowerLegLength*2-self.footHeight), startHeading)
        lowerLegVisual.clearModelNodes()
        footVisual.clearModelNodes()
        lowerLegVisual.flattenStrong()
        footVisual.flattenStrong()


        self.thigh.setPosHpr(startPosition, startHeading)
        self.lowerLeg.setPosHpr(startPosition, startHeading)


    # Resets the Z coordinate of the leg to a new value
    # FIXME: Incorrect positions
    # newZ: bottom of the foot's new Z position
    # returns: the top of the thigh's new Z position
    def setZ(self, newZ):
        lowerLegZ = self.footHeight+abs(sin(radians(self.lowerLeg.getP())))*self.lowerLegLength/2
        thighZ = lowerLegZ+abs(sin(radians(self.thigh.getP())))*self.thighLength/2
        self.lowerLeg.setZ(newZ+lowerLegZ)
        self.thigh.setZ(newZ+thighZ)
        return newZ+thighZ*2-lowerLegZ
