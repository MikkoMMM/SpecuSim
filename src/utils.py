from math import floor
from panda3d.core import Point3, BitMask32, TransformState

# TODO: compare speed to angleDeg in Panda's Vec3
def angle_diff(angle1, angle2):
    return (angle2 - angle1 + 180) % 360 - 180

def test_if_near_ground(bodypart, world, terrain_bullet_node, distance = 1000):
    pFrom = bodypart.get_pos()
    rc_result = world.ray_test_all(pFrom + Point3(0, 0, distance), pFrom - Point3(0, 0, distance))

    for hit in rc_result.get_hits():
        if hit.get_node() == terrain_bullet_node:
            return True
    return False

def get_object_ground_Z_pos(part, world, terrain_bullet_node, distance = 1000):
    pFrom = part.get_pos()
    return get_ground_Z_pos(pFrom.getX(), pFrom.getY(), world, terrain_bullet_node, distance)

def get_ground_Z_pos(x, y, world, terrain_bullet_node, distance = 1000):
    rc_result = world.ray_test_all(Point3(x, y, distance), Point3(x, y, -distance), BitMask32.bit(0))

    for hit in rc_result.get_hits():
        if hit.get_node() == terrain_bullet_node:
            return hit.get_hit_pos().getZ()
    return 0

# Warning: SLOW! (Use only if absolutely must.)
def get_collision_shape_ground_Z_pos(shape, x, y, world, terrain_bullet_node, distance = 1000):
    # It would be beneficial to take heading and pitch into account and this is indeed supported.
    # However, at 90 degree pitch the collision was sometimes at a really high place.
    ts_from = TransformState.make_pos(Point3(x, y, distance))
    ts_to = TransformState.make_pos(Point3(x, y, -distance))

    result = world.sweep_test_closest(shape, ts_from, ts_to, BitMask32.bit(0))
    if result.has_hit():
        return result.get_hit_pos().getZ()
    return 0


def normalize_angle(angle):
    angle = angle % 360
    if angle > 180:
        angle -= 360
    return angle
