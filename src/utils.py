from panda3d.core import PNMImage, Filename, PNMFileTypeRegistry
from panda3d.core import Point3, BitMask32, TransformState
from panda3d.core import SamplerState
from panda3d.core import ShaderTerrainMesh, Shader
from panda3d.core import Texture


# TODO: compare speed to angleDeg in Panda's Vec3
def angle_diff(angle1, angle2):
    return (angle2 - angle1 + 180) % 360 - 180


def test_if_near_ground(bodypart, world, terrain_bullet_node, distance=1000):
    p_from = bodypart.get_pos()
    rc_result = world.ray_test_all(p_from + Point3(0, 0, distance), p_from - Point3(0, 0, distance))

    for hit in rc_result.get_hits():
        if hit.get_node() == terrain_bullet_node:
            return True
    return False


def get_ground_z_pos(x, y, world, terrain_bullet_node, distance=1000):
    rc_result = world.ray_test_all(Point3(x, y, distance), Point3(x, y, -distance), BitMask32.bit(0))

    for hit in rc_result.get_hits():
        if hit.get_node() == terrain_bullet_node:
            return hit.get_hit_pos().getZ()
    return 0


# Warning: SLOW! (Use only if absolutely must.)
def get_collision_shape_ground_z_pos(shape, x, y, world, distance=1000):
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
            if ocean_map.get_green(x, y) == 0:
                image.set_gray(x, y, 1)
    png_type = PNMFileTypeRegistry.get_global_ptr().get_type_from_extension('.png')
    image.write(new_file, png_type)
    return image


def create_shader_terrain_mesh(elevation_img, height):
    elevation_img_size = elevation_img.get_x_size()
    elevation_img_offset = elevation_img_size / 2.0
    heightfield = Texture("heightfield")
    heightfield.load(elevation_img)
    heightfield.wrap_u = SamplerState.WM_clamp
    heightfield.wrap_v = SamplerState.WM_clamp

    # Construct the terrain
    terrain_node = ShaderTerrainMesh()
    terrain_node.heightfield = heightfield

    # Set the target triangle width. For a value of 10.0 for example,
    # the terrain will attempt to make every triangle 10 pixels wide on screen.
    terrain_node.target_triangle_width = 10.0

    # Generate the terrain
    terrain_node.generate()

    # Attach the terrain to the main scene and set its scale. With no scale
    # set, the terrain ranges from (0, 0, 0) to (1, 1, 1)
    terrain = render.attach_new_node(terrain_node)
    terrain.set_scale(elevation_img_size, elevation_img_size, height)
    terrain.set_pos(-elevation_img_offset, -elevation_img_offset, -height / 2)

    # Set a shader on the terrain. The ShaderTerrainMesh only works with
    # an applied shader. You can use the shaders used here in your own application
    terrain_shader = Shader.load(Shader.SL_GLSL, "shaders/terrain.vert.glsl", "shaders/terrain.frag.glsl")
    terrain.set_shader(terrain_shader)
    terrain.set_shader_input("camera", base.camera)

    return terrain
