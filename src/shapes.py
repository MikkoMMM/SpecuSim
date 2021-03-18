from panda3d.bullet import BulletCapsuleShape, BulletBoxShape, BulletSphereShape, BulletCylinderShape, BulletConeShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.core import BitMask32
from panda3d.bullet import ZUp
from panda3d.core import Vec3, TransformState, Point3

def create_physics_capsule(render, diameter, height):
    shape = BulletCapsuleShape(diameter/2, height-diameter, ZUp)
    node_path = render.attach_new_node(BulletRigidBodyNode())
    node_path.set_collide_mask(BitMask32.bit(1))
    node_path.node().add_shape(shape)
    node_path.node().set_angular_damping(0.9)
    node_path.node().set_friction(0.8)
    node_path.node().set_restitution(0.0)
    return node_path

def create_capsule(render, diameter, height, r=1, g=1, b=1, a=1):
    node_path = create_physics_capsule(render, diameter, height)
    visual = loader.load_model("3d-assets/unit_cylinder.bam")
    visual.set_scale(Vec3(diameter, diameter, height))
    visual.reparent_to(node_path)
    visual.set_color(r, g, b, a)
    return node_path


def create_physics_cone(render, diameter, height):
    shape = BulletConeShape(diameter/2, height, ZUp)
    node_path = render.attach_new_node(BulletRigidBodyNode())
    node_path.set_collide_mask(BitMask32.bit(1))
    node_path.node().add_shape(shape)
    node_path.node().set_angular_damping(0.9)
    node_path.node().set_friction(0.8)
    node_path.node().set_restitution(0.0)
    return node_path

def create_cone(render, diameter, height, r=1, g=1, b=1, a=1):
    node_path = create_physics_cone(render, diameter, height)
    visual = loader.load_model("3d-assets/unit_cone.bam")
    visual.set_scale(Vec3(diameter, diameter, height))
    visual.reparent_to(node_path)
    visual.set_color(r, g, b, a)
    return node_path


# A cuboid rounded from two sides
# NOTE: width has to be greater than depth
def create_physics_rounded_box(render, width, depth, height):
    node_path = render.attach_new_node(BulletRigidBodyNode())

    shape = BulletBoxShape(Vec3((width-depth)/2, depth/2, height/2))
    node_path.node().add_shape(shape)
    shape = BulletCylinderShape(depth/2, height, ZUp)
    node_path.node().add_shape(shape, TransformState.make_pos(Point3((-width+depth)/2, 0, 0)))
    node_path.node().add_shape(shape, TransformState.make_pos(Point3((width-depth)/2, 0, 0)))

    node_path.set_collide_mask(BitMask32.bit(1))
    node_path.node().set_angular_damping(0.9)
    node_path.node().set_friction(0.8)
    node_path.node().set_restitution(0.0)
    return node_path

def create_rounded_box(render, width, depth, height, r=1, g=1, b=1, a=1):
    node_path = create_physics_rounded_box(render, width, depth, height)
    visual = loader.load_model("3d-assets/unit_cylinder.bam")
    visual.set_scale(Vec3(width, depth, height))
    visual.reparent_to(node_path)
    visual.set_color(r, g, b, a)
    return node_path


def create_physics_box(render, dx, dy, dz):
    shape = BulletBoxShape(Vec3(dx/2, dy/2, dz/2))
    node_path = render.attach_new_node(BulletRigidBodyNode())
    node_path.set_collide_mask(BitMask32.bit(1))
    node_path.node().add_shape(shape)
    node_path.node().set_angular_damping(0.9)
    node_path.node().set_friction(0.8)
    node_path.node().set_restitution(0.0)
    return node_path

def create_box(render, dx, dy, dz, r=1, g=1, b=1, a=1):
    node_path = create_physics_box(render, dx, dy, dz)
    visual = loader.load_model("3d-assets/unit_cube.bam")
    visual.set_scale(Vec3(dx, dy, dz))
    visual.reparent_to(node_path)
    visual.set_color(r, g, b, a)
    return node_path


def create_physics_sphere(render, diameter):
    shape = BulletSphereShape(diameter/2)
    node_path = render.attach_new_node(BulletRigidBodyNode())
    node_path.set_collide_mask(BitMask32.bit(1))
    node_path.node().add_shape(shape)
    node_path.node().set_angular_damping(0.9)
    node_path.node().set_friction(0.8)
    node_path.node().set_restitution(0.0)
    return node_path

def create_sphere(render, diameter, r=1, g=1, b=1, a=1):
    node_path = create_physics_sphere(render, diameter)
    visual = loader.load_model("3d-assets/unit_sphere.bam")
    visual.set_scale(Vec3(diameter, diameter, diameter))
    visual.reparent_to(node_path)
    visual.set_color(r, g, b, a)
    return node_path
