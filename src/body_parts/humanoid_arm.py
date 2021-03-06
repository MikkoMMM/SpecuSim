from math import degrees, radians

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
    def __init__(self, world, height, upper_arm_diameter, forearm_diameter, right_arm, elbow_joint_force, start_position, start_heading):
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

        if right_arm:
            self.elbow_heading_limit = radians(-70)
            self.elbow.set_angular_limit(1, degrees(self.elbow_heading_limit), 0)
        else:
            self.elbow_heading_limit = radians(70)
            self.elbow.set_angular_limit(1, 0, degrees(self.elbow_heading_limit))

        self.elbow.set_angular_limit(0, -150, 0)

        self.elbow.set_angular_limit(2, 0, 0)
        self.elbow.set_debug_draw_size(0.5)
        self.world.attach_constraint(self.elbow, linked_collision=True)

        self.elbow_motor_pitch = self.elbow.get_rotational_limit_motor(0)
        self.elbow_motor_heading = self.elbow.get_rotational_limit_motor(1)
        self.elbow_motor_pitch.set_motor_enabled(True)
        self.elbow_motor_heading.set_motor_enabled(True)
        self.elbow_motor_heading.set_max_motor_force(elbow_joint_force)
        self.elbow_motor_pitch.set_max_motor_force(elbow_joint_force)
        self.elbow_motor_heading.set_max_limit_force(elbow_joint_force*10000)
        self.elbow_motor_pitch.set_max_limit_force(elbow_joint_force*10000)
        self.elbow_motor_pitch.set_bounce(2.5)
        self.elbow_motor_heading.set_bounce(2.5)

        self.upper_arm.set_pos_hpr(start_position, start_heading)
        self.forearm.set_pos_hpr(start_position, start_heading)


    def set_shoulder(self, frame_a, frame_a_node, arm_constraint_up, arm_constraint_down, arm_constraint_inward, arm_constraint_outward,
                     arm_force=30, bounciness=10):
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.upper_arm_length / 2), Vec3(0, -90, 0))
        self.shoulder = BulletGenericConstraint(frame_a_node, self.upper_arm.node(), frame_a, frame_b, False)
        self.shoulder.set_debug_draw_size(0.5)
        self.shoulder.set_angular_limit(0, degrees(arm_constraint_up), degrees(arm_constraint_down))
        self.shoulder.set_angular_limit(1, 0, 0)
        self.shoulder.set_angular_limit(2, degrees(arm_constraint_inward), degrees(arm_constraint_outward))
        self.upper_arm.node().set_angular_factor(Vec3(0.2, 0.2, 0.2))
        self.world.attach_constraint(self.shoulder, linked_collision=True)
        self.pitch_motor = self.shoulder.get_rotational_limit_motor(0)
        self.heading_motor = self.shoulder.get_rotational_limit_motor(2)
        self.pitch_motor.set_motor_enabled(True)
        self.heading_motor.set_motor_enabled(True)
        self.pitch_motor.set_max_motor_force(arm_force)
        self.heading_motor.set_max_motor_force(arm_force)
        self.pitch_motor.set_max_limit_force(arm_force*10000)
        self.heading_motor.set_max_limit_force(arm_force*10000)

        self.pitch_motor.set_bounce(bounciness)
        self.heading_motor.set_bounce(bounciness)


    def grab(self, attachment_info):
        if len(attachment_info) >= 4:
            self.grab_for_real(attachment_info[1], attachment_info[2], grab_angle=attachment_info[3])
        else:
            self.grab_for_real(attachment_info[1], attachment_info[2])


    def grab_for_real(self, target, grab_position, grab_angle=Vec3(0, 0, 0)):
        target.set_pos(self.forearm, Vec3(0, 0, 0))
        frame_a = TransformState.make_pos_hpr(Point3(0, 0, -self.forearm_length / 2), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(grab_position, grab_angle)

        self.hand = BulletGenericConstraint(self.forearm.node(), target.node(), frame_a, frame_b, True)
        self.hand.set_debug_draw_size(0.5)

        self.hand.set_angular_limit(0, -20, -20)
        self.hand.set_angular_limit(1, 0, 0)
        self.hand.set_angular_limit(2, 0, 0)
        self.world.attach_constraint(self.hand, linked_collision=True)


    def set_pos(self, new_pos):
        self.upper_arm.set_pos(new_pos)
        self.forearm.set_pos(new_pos)


    def get_mass(self):
        return self.upper_arm.node().get_mass() + self.forearm.node().get_mass()
