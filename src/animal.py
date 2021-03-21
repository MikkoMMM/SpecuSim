"""A parent class for animals.

This module handles any creature that is capable of locomotion in some form or another.
"""

from src.utils import get_ground_Z_pos
from math import cos, sin, radians, degrees
from panda3d.core import Vec3

class Animal():
    def __init__( self, render, world, terrain_bullet_node, body_node, feet, slope_difficult, slope_max, negligible_speed = 0.2 ):
        self.render = render
        self.world = world
        self.terrain_bullet_node = terrain_bullet_node
        self.body = body_node
        self.slope_difficult = slope_difficult
        self.slope_max = slope_max
        self.negligible_speed = negligible_speed
        self.feet = feet


    def get_correct_Z_velocity(self, current_Z_pos=None):
        # Too high and you'll get massive jittering at sharp points in the terrain physics node
        vector = self.body.node().get_linear_velocity()
        # Determine some Z change that is allowed. It's got to be low enough to reduce jitter.
        max_Z_change = 4*globalClock.get_dt()*min(self.walk_speed, 4*Vec3(vector.getX(), vector.getY(), 0).length())
        if current_Z_pos:
            return -min(max_Z_change,max(current_Z_pos,-max_Z_change))/globalClock.get_dt()
        return -min(max_Z_change,max(self.get_feet_averaged_ground_Z_pos(),-max_Z_change))/globalClock.get_dt()


    def get_feet_averaged_ground_Z_pos(self, offset_x=0, offset_y=0):
        average_x = 0
        average_y = 0
        average_z = 0
        for foot in self.feet:
            average_x += foot.getX(self.render)
            average_y += foot.getY(self.render)
            average_z += foot.getZ(self.render)-self.foot_height/2
        average_x /= len(self.feet)
        average_y /= len(self.feet)
        average_z /= len(self.feet)
        average_z -= get_ground_Z_pos(average_x+offset_x, average_y+offset_y, self.world, self.terrain_bullet_node)
        return average_z


    def walk_physics( self, speed, angle=0, decelerate=False ):
        if not decelerate:
            math_angle = radians(angle+90)
            diff = Vec3(-cos(math_angle),sin(math_angle),0)
            diff_n = diff.normalized()
            step = diff_n*speed

        current_Z_pos = self.get_feet_averaged_ground_Z_pos()
        preliminary_Z_velocity = self.get_correct_Z_velocity(current_Z_pos)
        if decelerate:
            new_vector = Vec3(self.body.node().get_linear_velocity().getX(), self.body.node().get_linear_velocity().getY(), preliminary_Z_velocity)
        else:
            ca = cos(radians(self.body.getH()))
            sa = sin(radians(self.body.getH()))
            new_vector = Vec3(ca*step.getX() - sa*step.getY(), sa*step.getX() + ca*step.getY(), preliminary_Z_velocity)
        z_diff = current_Z_pos - self.get_feet_averaged_ground_Z_pos(offset_x=new_vector.getX()*0.01, offset_y=new_vector.getY()*0.01)

        if z_diff > self.slope_difficult:
            mult = ((1/self.slope_max)*(self.slope_max-self.slope_difficult - (min(self.slope_max,z_diff)-self.slope_difficult)))
            self.body.node().set_linear_velocity(Vec3(new_vector.getX()*mult, new_vector.getY()*mult, preliminary_Z_velocity))
            if z_diff >= self.slope_max:
                return False
        else:
            self.body.node().set_linear_velocity(new_vector)

        # Negligible speed; assume we've come to a halt and save on resources
        if self.body.node().get_linear_velocity().length() < self.negligible_speed and abs(self.body.node().get_angular_velocity().getZ()) < 0.1:
            self.body.node().set_linear_velocity(Vec3(0,0,self.body.node().get_linear_velocity().getZ()))
            return False

        return True
