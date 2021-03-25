# Credit: Germanunkol

import math

from direct.task import Task
from panda3d.core import KeyboardButton, MouseButton
from panda3d.core import LPoint3, LVector3f
from panda3d.core import Quat


class CameraControl:

    def __init__(self, node, mouse_watcher_node, initial_heading=90, initial_pitch=65, initial_zoom=15):

        self.node = node
        self.focus_node = render.attach_new_node("CameraFocusNode")
        self.attachment_node = None
        self.attached = True

        self.focus_point = LPoint3()

        self.mouse_watcher_node = mouse_watcher_node

        self.b_forward = KeyboardButton.ascii_key('w')
        self.b_backward = KeyboardButton.ascii_key('s')
        self.b_left = KeyboardButton.ascii_key('a')
        self.b_right = KeyboardButton.ascii_key('d')
        self.b_speed = KeyboardButton.lshift()

        self.speed = 0.2

        self.zoom = initial_zoom

        self.ang = math.radians(initial_heading)
        self.angY = math.radians(initial_pitch)

        self.last_mouse_pos = (0, 0)


    def toggle_attachment(self):
        if self.attachment_node:
            self.attached = not self.attached
        else:
            self.attached = False


    def attach_to(self, other):

        self.attachment_node = other
        self.attached = True


    def wheel_up(self):

        self.zoom = self.zoom - 1
        self.zoom = min(max(self.zoom, 1), 2000)


    def wheel_down(self):

        self.zoom = self.zoom + 1
        self.zoom = min(max(self.zoom, 1), 2000)


    def move_camera(self, task):

        is_down = self.mouse_watcher_node.is_button_down

        if self.mouse_watcher_node.has_mouse():
            x = self.mouse_watcher_node.get_mouse_x()
            y = self.mouse_watcher_node.get_mouse_y()
            if is_down(MouseButton.two()):
                dx = self.last_mouse_pos[0] - x
                self.ang -= dx * 2
                # self.ang = max( 0, min( self.ang, math.pi*0.49 ) )
                dy = self.last_mouse_pos[1] - y
                self.angY -= dy * 2
                self.angY = max(0.01, min(self.angY, math.pi))
            if is_down(MouseButton.three()):
                dy = self.last_mouse_pos[1] - y
                self.zoom -= dy * 10
                self.zoom = min(max(self.zoom, 1), 2000)

            self.last_mouse_pos = (x, y)

        speed = self.speed
        if is_down(self.b_speed):
            speed = speed * 3

        if self.attachment_node and self.attached:
            self.focus_point = self.attachment_node.get_pos()
        else:
            sideways = (is_down(self.b_right) - is_down(self.b_left)) * speed
            forward = (is_down(self.b_forward) - is_down(self.b_backward)) * speed

            quat = Quat()
            quat.setFromAxisAngle(-180 * self.ang / math.pi, LVector3f.unitZ())
            rotated = quat.xform(LVector3f(-forward, sideways, 0))

            self.focus_point += rotated

        self.focus_node.set_pos(self.focus_point)

        radius = self.zoom
        self.angY = max(0, min(math.pi * 0.5, self.angY))
        r_y = math.sin(self.angY)
        if self.attached:
            # Reduce camera's bounciness
            #        if abs(self.camera.getZ(self.render)-self.old_camera_z) < 0.1:
            #            self.camera.setZ(self.render, self.old_camera_z)
            #        else:
            #            self.camera.setZ(self.render, (self.old_camera_z*2 + self.camera.getZ(self.render))/3)
            #        self.old_camera_z = self.camera.getZ(self.render)
            node_pos = LVector3f(r_y * math.cos(self.ang) * radius, -r_y * math.sin(self.ang) * radius,
                                 radius * math.cos(self.angY))
        else:  # Could also be used when reparented to render but there is a focus point
            node_pos = self.focus_point + LVector3f(r_y * math.cos(self.ang) * radius,
                                                    -r_y * math.sin(self.ang) * radius,
                                                    radius * math.cos(self.angY))

        self.node.set_pos(node_pos)
        self.node.look_at(self.focus_node)

        return Task.cont
