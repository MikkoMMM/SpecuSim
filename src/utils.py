from math import floor
from panda3d.core import Vec3

# TODO: compare speed to angleDeg in Panda's Vec3
def angleDiff(angle1, angle2):
    return (angle2 - angle1 + 180) % 360 - 180

def testIfNearGround(self, bodypart, distance, world, terrainBulletNode):
    pFrom = bodypart.getPos()
    rc_result = world.rayTestAll(pFrom + Vec3(0, 0, distance), pFrom - Vec3(0, 0, distance))

    for hit in rc_result.getHits():
        if hit.getNode() == terrainBulletNode:
            return True
    return False
