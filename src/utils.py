from math import floor
from panda3d.core import Point3, BitMask32

# TODO: compare speed to angleDeg in Panda's Vec3
def angleDiff(angle1, angle2):
    return (angle2 - angle1 + 180) % 360 - 180

def testIfNearGround(bodypart, world, terrainBulletNode, distance = 1000):
    pFrom = bodypart.getPos()
    rc_result = world.rayTestAll(pFrom + Point3(0, 0, distance), pFrom - Point3(0, 0, distance))

    for hit in rc_result.getHits():
        if hit.getNode() == terrainBulletNode:
            return True
    return False

def getObjectGroundZPos(part, world, terrainBulletNode, distance = 1000):
    pFrom = part.getPos()
    return getGroundZPos(pFrom.getX(), pFrom.getY(), world, terrainBulletNode, distance)

def getGroundZPos(x, y, world, terrainBulletNode, distance = 1000):
    rc_result = world.rayTestAll(Point3(x, y, distance), Point3(x, y, -distance), BitMask32.allOn())

    for hit in rc_result.getHits():
        if hit.getNode() == terrainBulletNode:
            return hit.getHitPos().getZ()
    return 0

def normalizeAngle(angle):
    angle = angle % 360
    if angle > 180:
        angle -= 360
    return angle
