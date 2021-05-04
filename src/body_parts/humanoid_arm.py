from panda3d.bullet import BulletGenericConstraint
from panda3d.core import BitMask32, Point3, TransformState
from panda3d.core import Vec3

from src.shapes import create_capsule


class HumanoidArm:
    # Arguments:
    # world: A BulletWorld to use for physics
    # upper_arm_diameter: upper_arm's diameter
    # forearm_diameter: forearm's diameter
    # height: arm's total height
    def __init__(self, world, height, upper_arm_diameter, forearm_diameter, right_arm, start_position, start_heading):
        self.world = world

        self.upper_arm_length = height * 50 / 100
        self.forearm_length = height * 50 / 100
        self.upper_arm_diameter = upper_arm_diameter

        self.upper_arm = create_capsule(self.upper_arm_diameter, self.upper_arm_length)
        self.upper_arm.node().set_angular_sleep_threshold(0)
        self.upper_arm.node().set_mass(2.0)
        self.world.attach(self.upper_arm.node())

        self.forearm = create_capsule(forearm_diameter, self.forearm_length)
        self.forearm.node().set_angular_sleep_threshold(0)
        self.forearm.set_collide_mask(BitMask32.bit(3))
        self.forearm.node().set_mass(1.0)
        self.world.attach(self.forearm.node())

        frame_a = TransformState.make_pos_hpr(Point3(0, 0, -self.upper_arm_length / 2), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.forearm_length / 2), Vec3(0, 0, 0))

        self.elbow = BulletGenericConstraint(self.upper_arm.node(), self.forearm.node(), frame_a, frame_b, True)

        self.elbow.set_angular_limit(0, -165, 0)
        if right_arm:
            self.elbow.set_angular_limit(1, -30, 0)
        else:
            self.elbow.set_angular_limit(1, 0, 30)

        self.elbow.set_angular_limit(2, 0, 0)
        self.elbow.set_debug_draw_size(0.5)
        self.world.attach_constraint(self.elbow, linked_collision=True)

        self.upper_arm.set_pos_hpr(start_position, start_heading)
        self.forearm.set_pos_hpr(start_position, start_heading)


    def grab(self, attachment_info):
        if len(attachment_info) >= 4:
            self.grab_for_real(attachment_info[1], attachment_info[2], grab_angle=attachment_info[3])
        else:
            self.grab_for_real(attachment_info[1], attachment_info[2])


    def grab_for_real(self, target, grab_position, grab_angle=Vec3(0, 0, 0)):
        frame_a = TransformState.make_pos_hpr(Point3(0, 0, -self.forearm_length / 2), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(grab_position, grab_angle)

        self.hand = BulletGenericConstraint(self.forearm.node(), target.node(), frame_a, frame_b, True)
        self.hand.set_debug_draw_size(0.5)
        self.hand.set_angular_limit(0, -180, 180)
        self.hand.set_angular_limit(1, -180, 180)
        self.hand.set_angular_limit(2, -180, 180)
        self.world.attach_constraint(self.hand, linked_collision=True)


    def set_pos(self, new_pos):
        self.upper_arm.set_pos(new_pos)
        self.forearm.set_pos(new_pos)


    def get_mass(self):
        return self.upper_arm.node().get_mass() + self.forearm.node().get_mass()
