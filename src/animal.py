"""A parent class for animals.

This module handles any creature that is capable of locomotion in some form or another.
"""

from math import cos, sin, radians, degrees, acos, copysign

from panda3d.core import Vec2, Vec3

from src.utils import get_ground_z_pos
from datetime import datetime
from src.language_processing.nlp_manager import NLPManager


class Animal:
    """A parent class for animals.

    Args:
        world (BulletWorld): A BulletWorld to use for physics
        terrain_bullet_node (BulletRigidBodyNode): A Bullet node that has elevation information in its collision shape
        body_node (NodePath): A NodePath to apply velocity to, and whose velocity is treated as the whole organism's velocity
        feet (List[NodePath]): A list of feet
        slope_difficult (float): The angle in degrees at which steepness of slope the organism's movement should start slowing down
        slope_max (float): The angle in degrees which is too steep to climb
        slope_linear_damping (float): Linear damping exponent while climbing
        negligible_speed (float, optional): Speed in m/s below which it's assumed the organism is at halt
        debug_text_node (OnscreenText, optional): A place in the GUI to write debug information to
    """

    def __init__(self, world, terrain_bullet_node, body_node, feet, slope_difficult, slope_max,
                 slope_linear_damping=0.6, negligible_speed=0.2, debug_text_node=None):
        self.world = world
        self.terrain_bullet_node = terrain_bullet_node
        self.body = body_node
        self.slope_difficult = radians(slope_difficult)
        self.slope_max = radians(slope_max)
        self.negligible_speed = negligible_speed
        self.feet = feet
        self.debug_text_node = debug_text_node
        self.slope_linear_damping = slope_linear_damping
        self.speech_field = None
        # We store this here, in case somebody wants to switch speech bubble styles
        self.can_talk_time = datetime(1, 1, 1, 1, 1, 1, 342380)
        self.can_talk_more = True


    def get_body(self):
        """Gets the organism's main body node

        Returns:
            NodePath: the main body node
        """
        return self.body


    def hide_speech_field(self):
        with NLPManager.lock:
            self.speech_field.hide()


    def set_speech_field(self, speech_field):
        """Sets where to output what this animal says.

        Args:
            speech_field: Any object that has a set_text method
        """
        self.speech_field = speech_field


    def say(self, text):
        """Sets the speech field's (if it exists) text to the given argument

        Args:
            text (str): The text to say
        """
        if self.speech_field:
            self.speech_field.set_text(text)
            on_screen_time = max(30.0/NLPManager.talking_speed, len(text) / NLPManager.talking_speed)
            if self.speech_field.hide_task:
                taskMgr.remove(self.speech_field.hide_task)
            self.speech_field.hide_task = taskMgr.doMethodLater(on_screen_time, self.hide_speech_field, 'HSB', extraArgs=[])


    def get_ground_z_velocity(self, current_z_pos=None):
        """Calculates a vertical velocity at which the creature will stay on the surface of the terrain

        Args:
            current_z_pos (float, optional): The return value of get_body_ground_z_pos()

        Returns:
            float: The vertical velocity in m/s at which the creature will stay on the surface of the terrain
        """

        # Too high and you'll get massive jittering at sharp points in the terrain physics node
        vector = self.body.node().get_linear_velocity()
        # Determine some Z change that is allowed. It's got to be low enough to reduce jitter.
        max_z_change = 4 * globalClock.get_dt() * 4 * Vec3(vector.getX(), vector.getY(), 0).length()
        if current_z_pos:
            return -min(max_z_change, max(current_z_pos, -max_z_change)) / globalClock.get_dt()
        return -min(max_z_change, max(self.get_body_ground_z_pos(), -max_z_change)) / globalClock.get_dt()


    def get_body_ground_z_pos(self, offset_x=0, offset_y=0):
        """Calculates where the body should be located on the Z axis

        Args:
            offset_x (float, optional): offset on the X axis from the central point of the creature to get the elevation
            offset_y (float, optional): offset on the Y axis from the central point of the creature to get the elevation
        """
        average_z = 0
        for foot in self.feet:
            average_z += foot.getZ(render)
        average_z /= len(self.feet)

        average_z -= get_ground_z_pos(self.body.getX() + offset_x, self.body.getY() + offset_y, self.world,
                                      self.terrain_bullet_node)
        return average_z


    def walk_physics(self, speed, angle=0, decelerate=False):
        """Sets the linear velocity of the creature while keeping it on the ground.

        Args:
            speed (float): Movement speed in m/s, assuming flat ground.
            angle (float): The absolute angle in which to move, in radians
            decelerate (bool, optional): Whether to actively move (False) or to let movement come to a natural halt over time (True)

        Returns:
            bool: Whether the organism actually moved at all.
        """

        current_z_pos = self.get_body_ground_z_pos()
        preliminary_z_velocity = self.get_ground_z_velocity(current_z_pos)
        if decelerate:
            new_vector = Vec3(self.body.node().get_linear_velocity().getX(),
                              self.body.node().get_linear_velocity().getY(), preliminary_z_velocity)
        else:
            math_angle = angle
            diff = Vec3(-cos(math_angle), sin(math_angle), 0)
            diff_n = diff.normalized()
            step = diff_n * speed

            ca = cos(radians(self.body.getH()))
            sa = sin(radians(self.body.getH()))
            new_vector = Vec3(ca * step.getX() - sa * step.getY(), sa * step.getX() + ca * step.getY(),
                              preliminary_z_velocity)

        eps_x = new_vector.getX() * 0.01
        eps_y = new_vector.getY() * 0.01
        z_diff = current_z_pos - self.get_body_ground_z_pos(offset_x=eps_x, offset_y=eps_y)
        eps_dist = Vec2(eps_x, eps_y).length()
        new_vec_dist = Vec3(eps_x, eps_y, z_diff).length()
        if new_vec_dist > 0 and new_vec_dist >= eps_dist:
            vertical_angle = copysign(acos(eps_dist / new_vec_dist), z_diff)
            if self.debug_text_node:
                self.debug_text_node.text = "Angle: " + str(round(degrees(vertical_angle), 1))
        else:
            vertical_angle = 0

        if vertical_angle > self.slope_difficult:
            if vertical_angle >= self.slope_max:
                self.body.node().set_linear_velocity(Vec3(0, 0, preliminary_z_velocity))
                return False

            normalized = (vertical_angle - self.slope_difficult) / (self.slope_max - self.slope_difficult)
            # Bullet's code has this regarding linear damping:
            # m_linearVelocity *= btPow(btScalar(1) - m_linearDamping, timeStep);

            mult = pow(1 - normalized, self.slope_linear_damping)
            if decelerate:
                mult = pow(1 - mult, globalClock.get_dt())
            self.body.node().set_linear_velocity(
                Vec3(new_vector.getX() * mult, new_vector.getY() * mult, preliminary_z_velocity))
        else:
            self.body.node().set_linear_velocity(new_vector)

        # Negligible speed; assume we've come to a halt and save on resources
        if self.body.node().get_linear_velocity().length() < self.negligible_speed and abs(
                self.body.node().get_angular_velocity().getZ()) < 0.1:
            self.body.node().set_linear_velocity(Vec3(0, 0, self.body.node().get_linear_velocity().getZ()))
            return False

        return True
