from math import floor
from panda3d.core import Point3, BitMask32, TransformState
from panda3d.core import PNMImage, Filename, PNMFileTypeRegistry

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

def get_ground_z_pos(x, y, world, terrain_bullet_node, distance = 1000):
    rc_result = world.ray_test_all(Point3(x, y, distance), Point3(x, y, -distance), BitMask32.bit(0))

    for hit in rc_result.get_hits():
        if hit.get_node() == terrain_bullet_node:
            return hit.get_hit_pos().getZ()
    return 0

# Warning: SLOW! (Use only if absolutely must.)
def get_collision_shape_ground_z_pos(shape, x, y, world, terrain_bullet_node, distance = 1000):
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


def create_or_load_walk_map(file_name_prefix, ocean_map_file):
    file_name = file_name_prefix + ".walk"
    new_file = Filename(file_name)
    if new_file.exists():
        return PNMImage(new_file)
    image = PNMImage(Filename(file_name_prefix))
    ocean_map = PNMImage(Filename(ocean_map_file))
    for x in range(ocean_map.get_x_size()):
        for y in range(ocean_map.get_y_size()):
            if ocean_map.get_green(x,y) == 0:
                image.set_gray(x,y,1)
    PNG_TYPE = PNMFileTypeRegistry.get_global_ptr().get_type_from_extension('.png')
    image.write(new_file, PNG_TYPE)
    return image
