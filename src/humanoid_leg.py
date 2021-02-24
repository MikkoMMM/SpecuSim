from panda3d.bullet import BulletCapsuleShape, BulletCylinderShape
from panda3d.core import Vec3
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.bullet import BulletHingeConstraint, BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import ZUp
from src.shapes import createCapsule, createBox

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

        self.thigh = createCapsule(self.render, thighDiameter, self.thighLength)
        self.thigh.node().setMass(10.0)
        self.world.attachRigidBody(self.thigh.node())
        visual = loader.loadModel("models/unit_cylinder.bam")
        visual.setScale(Vec3(thighDiameter, thighDiameter, self.thighLength))
        visual.reparentTo(self.thigh)
        visual.clearModelNodes()


        self.lowerLeg = createCapsule(self.render, lowerLegDiameter*2.2, self.lowerLegLength+self.footHeight*2)
        self.lowerLeg.node().setMass(5.0)
        self.world.attachRigidBody(self.lowerLeg.node())
        visual = loader.loadModel("models/unit_cylinder.bam")
        visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter, self.lowerLegLength))
        visual.reparentTo(self.lowerLeg)
        visual.clearModelNodes()
        self.lowerLeg.setCollideMask(BitMask32.bit(2)) # Collides with ground

        frameA = TransformState.makePosHpr(Point3(0,0,-self.thighLength/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0,0,self.lowerLegLength/2), Vec3(0, 0, 0))

        self.knee = BulletGenericConstraint(self.thigh.node(), self.lowerLeg.node(), frameA, frameB, True)

        self.knee.setDebugDrawSize(2.0)
        self.knee.setAngularLimit(0, 0, 45)
        self.knee.setAngularLimit(1, 0, 0)
        self.knee.setAngularLimit(2, 0, 0)
        self.world.attachConstraint(self.knee, linked_collision=True)


        # The feet are special in that they collide with the ground and their physics boxes are larger height-wise than the visuals
        self.foot = createBox(self.render, lowerLegDiameter, lowerLegDiameter*2.2, self.footHeight)
        self.foot.node().setMass(1.0)
        self.world.attachRigidBody(self.foot.node())
        visual = loader.loadModel("models/unit_cube.bam")
        visual.setScale(Vec3(lowerLegDiameter, lowerLegDiameter*2.2, self.footHeight))
        visual.reparentTo(self.foot)
        visual.clearModelNodes()
        #self.foot.setCollideMask(BitMask32.bit(2)) # Collides with ground
#        self.foot.node().setAngularFactor(Vec3(0.1,0.1,1))

        frameA = TransformState.makePosHpr(Point3(0,lowerLegDiameter/6,-self.lowerLegLength/2), Vec3(0, 0, 0))
        frameB = TransformState.makePosHpr(Point3(0,-lowerLegDiameter/6,self.footHeight/2), Vec3(0, 0, 0))

        self.heel = BulletGenericConstraint(self.lowerLeg.node(), self.foot.node(), frameA, frameB, True)

        self.heel.setDebugDrawSize(2.0)
        self.heel.setAngularLimit(0, -45, 45)
        self.heel.setAngularLimit(1, 0, 0)
        self.heel.setAngularLimit(2, 0, 0)
        self.world.attachConstraint(self.heel, linked_collision=True)


        self.thigh.setPosHpr(startPosition, startHeading)
        self.lowerLeg.setPosHpr(startPosition, startHeading)
        self.foot.setPosHpr(startPosition, startHeading)
