"""A parent class for animals.

This module handles any creature that is capable of locomotion in some form or another.
"""

from src.utils import get_ground_Z_pos
from math import cos, sin, radians, degrees, acos, copysign
from panda3d.core import Vec2, Vec3

class Animal():
    """A parent class for animals.

    Args:
        render (NodePath): A NodePath to get relative positions for
        world (BulletWorld): A BulletWorld to use for physics
        terrain_bullet_node (BulletRigidBodyNode): A Bullet node that has elevation information in its collision shape
        body_node (NodePath): A NodePath to apply velocity to, and whose velocity is treated as the whole organism's velocity
        feet (List[NodePath]): A list of feet
        slope_difficult (float): The angle in degrees at which steepness of slope the organism's movement should start slowing down
        slope_max (float): The angle in degrees which is too steep to climb
        slope_linear_damping_moving (float): Linear damping multiplier while moving on a slope
        slope_linear_damping_decelerating (float): Linear damping multiplier while decelerating on a slope
        negligible_speed (float, optional): Speed in m/s below which it's assumed the organism is at halt
        debug_text_node (OnscreenText, optional): A place in the GUI to write debug information to
    """

    def __init__( self, render, world, terrain_bullet_node, body_node, feet, slope_difficult, slope_max, slope_linear_damping_moving = 30, slope_linear_damping_decelerating = 3, negligible_speed = 0.2, debug_text_node = None ):
        self.render = render
        self.world = world
        self.terrain_bullet_node = terrain_bullet_node
        self.body = body_node
        self.slope_difficult = radians(slope_difficult)
        self.slope_max = radians(slope_max)
        self.negligible_speed = negligible_speed
        self.feet = feet
        self.debug_text_node = debug_text_node
        self.slope_linear_damping_moving = slope_linear_damping_moving
        self.slope_linear_damping_decelerating = slope_linear_damping_decelerating


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
        max_Z_change = 4*globalClock.get_dt()*min(self.walk_speed, 4*Vec3(vector.getX(), vector.getY(), 0).length())
        if current_z_pos:
            return -min(max_Z_change,max(current_z_pos,-max_Z_change))/globalClock.get_dt()
        return -min(max_Z_change,max(self.get_body_ground_z_pos(),-max_Z_change))/globalClock.get_dt()


    def get_body_ground_z_pos(self, offset_x=0, offset_y=0):
        """Calculates where the body should be located on the Z axis

        Args:
            offset_x (float, optional): offset on the X axis from the central point of the creature to get the elevation
            offset_y (float, optional): offset on the Y axis from the central point of the creature to get the elevation
        """
        average_z = 0
        for foot in self.feet:
            average_z += foot.getZ(self.render)-self.foot_height/2
        average_z /= len(self.feet)

        average_z -= get_ground_Z_pos(self.body.getX()+offset_x, self.body.getY()+offset_y, self.world, self.terrain_bullet_node)
        return average_z


    def walk_physics( self, speed, angle=0, decelerate=False ):
        """Sets the linear velocity of the creature while keeping it on the ground.
            TODO: Finish documentation

        Args:
            speed (float): Movement speed in m/s, assuming flat ground.
        """
        if not decelerate:
            math_angle = radians(angle+90)
            diff = Vec3(-cos(math_angle),sin(math_angle),0)
            diff_n = diff.normalized()
            step = diff_n*speed

        current_z_pos = self.get_body_ground_z_pos()
        preliminary_Z_velocity = self.get_ground_z_velocity(current_z_pos)
        if decelerate:
            new_vector = Vec3(self.body.node().get_linear_velocity().getX(), self.body.node().get_linear_velocity().getY(), preliminary_Z_velocity)
        else:
            ca = cos(radians(self.body.getH()))
            sa = sin(radians(self.body.getH()))
            new_vector = Vec3(ca*step.getX() - sa*step.getY(), sa*step.getX() + ca*step.getY(), preliminary_Z_velocity)

        eps_x = new_vector.getX()*0.01
        eps_y = new_vector.getY()*0.01
        z_diff = current_z_pos - self.get_body_ground_z_pos(offset_x=eps_x, offset_y=eps_y)
        eps_dist = Vec2(eps_x, eps_y).length()
        new_vec_dist = Vec3(eps_x, eps_y, z_diff).length()
        if new_vec_dist > 0 and new_vec_dist >= eps_dist:
            vertical_angle = copysign(acos(eps_dist/new_vec_dist), z_diff)
            if self.debug_text_node:
                self.debug_text_node.text = "Angle: " + str(round(degrees(vertical_angle),1))
        else:
            vertical_angle = 0

        if vertical_angle > self.slope_difficult:
            # Returns near 0 when nearing max slope
            one_minus_damping = ((1/self.slope_max)*(self.slope_max-self.slope_difficult - (min(self.slope_max,vertical_angle)-self.slope_difficult)))
            # Bullet's code has this regarding linear damping:
            # m_linearVelocity *= btPow(btScalar(1) - m_linearDamping, timeStep);
#            self.body.node().set_linear_velocity(Vec3(new_vector.getX()*mult, new_vector.getY()*mult, preliminary_Z_velocity))
            if decelerate:
                power = pow(one_minus_damping,globalClock.get_dt()*self.slope_linear_damping_decelerating)
            else:
                power = pow(one_minus_damping,globalClock.get_dt()*self.slope_linear_damping_moving)
            self.body.node().set_linear_velocity(Vec3(new_vector.getX()*power, new_vector.getY()*power, preliminary_Z_velocity))
            if vertical_angle >= self.slope_max:
                return False
        else:
            self.body.node().set_linear_velocity(new_vector)

        # Negligible speed; assume we've come to a halt and save on resources
        if self.body.node().get_linear_velocity().length() < self.negligible_speed and abs(self.body.node().get_angular_velocity().getZ()) < 0.1:
            self.body.node().set_linear_velocity(Vec3(0,0,self.body.node().get_linear_velocity().getZ()))
            return False

        return True
