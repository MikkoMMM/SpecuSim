import struct
from math import radians

from src.animal import Animal
from src.inverse_kinematics.IKChain import IKChain
from src.inverse_kinematics.Utils import *
from src.inverse_kinematics.WalkCycle import WalkCycle
from src.inverse_kinematics.ArmatureUtils import ArmatureUtils
from src.shapes import create_rounded_box
from src.speech_bubble import SpeechBubble
from src.utils import angle_diff, normalize_angle, get_ground_z_pos


class Humanoid(Animal):
    """A class for humanoid animals.
    """


    def __init__(self, world, terrain_bullet_node, x, y, height=1.7, start_heading=Vec3(0, 0, 0), debug=False, debug_text_node=None):
        self.world = world
        self.terrain_bullet_node = terrain_bullet_node
        self.debug = debug

        # Initialize body proportions
        self.height = height
        self.head_height = self.height / 7
        self.chest_width = 0.38
        self.pelvis_width = 0.38
        self.lower_torso_height = 1.4 * (self.height / 7)
        self.chest_height = 1.6 * (self.height / 7)

        self.leg_height = self.height - self.head_height - self.lower_torso_height - self.chest_height
        self.thigh_length = self.leg_height * 59 / 109
        thigh_diameter = self.pelvis_width / 2 - 0.01
        self.lower_leg_length = self.leg_height * 40 / 109
        lower_leg_diameter = (self.pelvis_width / 2 - 0.01) * self.leg_height
        self.foot_height = self.leg_height - self.thigh_length - self.lower_leg_length
        self.foot_length = lower_leg_diameter * 2.2

        self.arm_height = self.leg_height * 1
        self.upper_arm_length = self.arm_height * 50 / 100
        upper_arm_diameter = self.chest_width / 3 - 0.01
        self.forearm_length = self.arm_height * 50 / 100
        forearm_diameter = (self.chest_width / 3 - 0.01) * self.arm_height

        self.target_height = self.leg_height + self.lower_torso_height / 2

        # Control node and the whole body collision box
        self.lower_torso = create_rounded_box(self.chest_width, 0.2, self.lower_torso_height)
        start_position = Vec3(x, y, self.target_height + get_ground_z_pos(x, y, self.world, self.terrain_bullet_node))
        self.lower_torso.set_pos_hpr(start_position, start_heading)
        self.lower_torso.node().set_mass(70.0)
        self.lower_torso.node().set_angular_factor(Vec3(0, 0, 0.1))
        self.lower_torso.node().set_linear_damping(0.8)
        self.lower_torso.node().set_angular_sleep_threshold(0)  # Sleep would freeze the whole character if still
        self.lower_torso.set_collide_mask(
            BitMask32.bit(0 | 3))  # Enable ground collision too, to help with avoiding ascending map boundaries
        self.world.attach(self.lower_torso.node())

        self.spine = self.lower_torso.attach_new_node("spine")
        self.spine.set_z(self.lower_torso_height / 2)

        self.chest = loader.load_model("3d-assets/unit_cylinder.bam")
        self.chest.set_scale(Vec3(self.chest_width, 0.2, self.chest_height))
        self.chest.reparent_to(self.spine)
        self.chest.set_z(self.chest_height / 2)

        self.head = loader.load_model("3d-assets/unit_sphere.bam")
        self.head.reparent_to(self.chest)
        self.head.set_scale(render, self.head_height)
        self.head.set_z((self.lower_torso_height + self.head_height) / 2 / self.lower_torso_height)

        '''
        self.left_arm = HumanoidArm(self.world, self.arm_height, upper_arm_diameter,
                                    forearm_diameter, False, start_position, start_heading)

        frame_a = TransformState.make_pos_hpr(Point3(-self.chest_width / 2 - self.left_arm.upper_arm_diameter / 2, 0,
                                                     self.chest_height / 2 - self.left_arm.upper_arm_diameter / 8), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.left_arm.upper_arm_length / 2), Vec3(0, -90, 0))

        self.left_arm_constraint = BulletGenericConstraint(self.chest.node(), self.left_arm.upper_arm.node(), frame_a, frame_b, True)
        self.left_arm_constraint.set_debug_draw_size(0.5)
        self.left_arm_constraint.set_angular_limit(0, -95, 135)  # Front and back
        self.left_arm_constraint.set_angular_limit(1, 0, 0)  # Rotation, handled in the elbow joint because here it glitches.
        self.left_arm_constraint.set_angular_limit(2, -120, 35)  # Left and right
        self.left_arm.upper_arm.node().set_angular_factor(Vec3(0.2, 0.2, 0.2))
        self.world.attach_constraint(self.left_arm_constraint, linked_collision=True)

        self.right_arm = HumanoidArm(self.world, self.arm_height, upper_arm_diameter,
                                     forearm_diameter, True, start_position, start_heading)

        frame_a = TransformState.make_pos_hpr(Point3(self.chest_width / 2 + self.right_arm.upper_arm_diameter / 2, 0,
                                                     self.chest_height / 2 - self.right_arm.upper_arm_diameter / 8), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.right_arm.upper_arm_length / 2), Vec3(0, -90, 0))

        self.right_arm_constraint = BulletGenericConstraint(self.chest.node(), self.right_arm.upper_arm.node(), frame_a, frame_b, True)
        self.right_arm_constraint.set_debug_draw_size(0.5)
        self.right_arm_constraint.set_angular_limit(0, -95, 135)  # Front and back
        self.right_arm_constraint.set_angular_limit(1, 0, 0)  # Rotation, handled in the elbow joint because here it glitches.
        self.right_arm_constraint.set_angular_limit(2, -35, 120)  # Left and right
        self.right_arm.upper_arm.node().set_angular_factor(Vec3(0.2, 0.2, 0.2))
        self.world.attach_constraint(self.right_arm_constraint, linked_collision=True)
        '''

        ##################################
        # Set up Armature and Joints:
        au = ArmatureUtils()

        ##################################
        # Set up body movement:
        self.walk_speed = 2  # m/s

        # Set up information needed by inverse kinematics
        self.thigh = []
        lower_leg = []
        self.foot = []
        self.leg = []
        self.foot_target = []
        self.planned_foot_target = []

        for i in range(2):
            if i == 0:
                horizontal_placement = -1
            else:
                horizontal_placement = 1

            # Place the hip
            rootJoint = au.createJoint("root" + str(i))

            # Hip:
            self.thigh.append(au.createJoint( "upperLeg" + str(i), parentJoint=rootJoint,
                translate=Vec3(horizontal_placement * self.pelvis_width / 4, 0, -self.lower_torso_height / 2) ))

            lower_leg.append(au.createJoint("lowerLeg" + str(i), parentJoint=self.thigh[i], translate=-LVector3f.unitZ() *
                                                                                                      self.thigh_length))
            foot_joint = au.createJoint("foot" + str(i), parentJoint=lower_leg[i], translate=-LVector3f.unitZ() * self.lower_leg_length)

            # IMPORTANT! Let the ArmatureUtils create the actor and set up control nodes:
            au.finalize()
            # IMPORTANT! Attach the created actor to the scene, otherwise you won't see anything!
            au.getActor().reparentTo(self.lower_torso)

            self.foot.append(au.getControlNode( foot_joint.getName() ).attach_new_node("Foot"))
            self.foot[i].set_pos_hpr(Vec3(0, self.foot_height / 2, 0), Vec3(0, 0, 0))

            self.leg.append(IKChain(au.getActor()))

            #        bone = self.ikChainLegLeft.addJoint( hipL, au.getControlNode( hipL.getName() ) )
            bone = self.leg[i].addJoint(self.thigh[i], au.getControlNode(self.thigh[i].getName()))
            bone = self.leg[i].addJoint(lower_leg[i], au.getControlNode(lower_leg[i].getName()), parentBone=bone)
            bone = self.leg[i].addJoint(foot_joint, au.getControlNode(foot_joint.getName()), parentBone=bone)

            self.leg[i].setBallConstraint(self.thigh[i].getName(), minAng=-math.pi * 0.2, maxAng=math.pi * 0.2)
            self.leg[i].setHingeConstraint(lower_leg[i].getName(), LVector3f.unitX(), minAng=-math.pi * 0.7, maxAng=0)
            self.leg[i].setBallConstraint(foot_joint.getName(), minAng=0, maxAng=math.pi * 0.6)

            if self.debug:
                self.leg[i].debugDisplay()

            #################################################
            # Foot targets:

            # Set up a target that the foot should reach:
            self.foot_target.append(render.attach_new_node("FootTarget"))
            self.foot_target[i].setZ(
                self.target_height + get_ground_z_pos(self.foot_target[i].getX(), self.foot_target[i].getY(), self.world,
                                                      self.terrain_bullet_node))
            self.leg[i].setTarget(self.foot_target[i])

            # Set up nodes which stay (rigidly) infront of the body, on the floor.
            # Whenever a leg needs to take a step, the target will be placed on this position:
            self.planned_foot_target.append(self.lower_torso.attach_new_node("PlannedFootTarget"))
            step_dist = 0.35
            self.planned_foot_target[i].set_pos(horizontal_placement * self.pelvis_width / 4, step_dist, -self.target_height)

            if self.debug:
                geom = createAxes(0.2)
                self.foot_target[i].attach_new_node(geom)
                self.planned_foot_target[i].attach_new_node(geom)

            # Add visuals to the bones. These MUST be after finalize().

            visual = loader.load_model("3d-assets/unit_cylinder.bam")
            visual.set_scale(Vec3(thigh_diameter, thigh_diameter, self.thigh_length))
            visual.reparent_to(au.getControlNode(self.thigh[i].getName()))
#            visual.set_pos((visual.get_pos() + lower_leg[i].offset) / 2)
            visual.set_pos((visual.get_pos() - LVector3f.unitZ() * self.thigh_length) / 2)

            visual = loader.load_model("3d-assets/unit_cylinder.bam")
            visual.set_scale(Vec3(lower_leg_diameter, lower_leg_diameter, self.lower_leg_length))
            visual.reparent_to(au.getControlNode(lower_leg[i].getName()))
#            visual.set_pos((visual.get_pos() + bone.offset) / 2)
            visual.set_pos((visual.get_pos() - LVector3f.unitZ() * self.lower_leg_length) / 2)

            foot_visual = loader.load_model("3d-assets/unit_cube.bam")
            foot_visual.reparent_to(self.foot[i])
            foot_visual.set_scale(Vec3(lower_leg_diameter, self.foot_length, self.foot_height))

        self.lower_torso.node().set_gravity(Vec3(0, 0, 0))

        self.leg_movement_speed = self.walk_speed * 3

        self.step_left = False
        self.step_right = False

        self.walk_cycle = WalkCycle(2, 0.75)
        self.desired_heading = self.lower_torso.getH()

        super().__init__(world, terrain_bullet_node, body_node=self.lower_torso, feet=self.foot, slope_difficult=20, slope_max=50,
                         debug_text_node=debug_text_node)

        # Humanoids automatically come equipped with a speaking capability. Neat, huh?
        self.set_speech_field(
            SpeechBubble(self.get_body(), self.lower_torso_height + self.chest_height + self.head_height + self.height * 0.2))


    def speed_up(self):
        self.walk_speed += 0.1
        self.walk_speed = min(self.walk_speed, 9)
        self.leg_movement_speed = self.walk_speed * 3


    def slow_down(self):
        self.walk_speed -= 0.1
        self.walk_speed = max(self.walk_speed, 0)
        self.leg_movement_speed = self.walk_speed * 3


    def stand_still(self):
        """Stand still. Please call this method if you didn't call walk_in_dir this frame.
        """
        self.walk_in_dir(self.lower_torso.getH(), decelerate=True)


    def walk_in_dir(self, angle=0, visuals=True, decelerate=False):
        """Walk in the given direction. Please call this method or stand_still exactly once every frame.
        """
        did_move = self.walk_physics(self.walk_speed, angle=angle, decelerate=decelerate)
        if did_move and visuals:
            # Calculate how far we've walked this frame:
            cur_walk_dist = self.lower_torso.node().get_linear_velocity().length() * globalClock.get_dt()
            self._walking_visuals(cur_walk_dist, 0)
        # The heading should be updated exactly once per frame, so let's do it here
        self._update_heading()
        self._update_spine()


    def _walking_visuals(self, cur_walk_dist, ang_clamped):
        #############################
        # Update legs:

        # Move planned foot target further forward (longer steps) when character is
        # walking faster:
        step_dist = cur_walk_dist * 0.1 / globalClock.get_dt()
        left = 0
        right = 1
        self.planned_foot_target[left].set_pos(-self.pelvis_width / 4, step_dist, -self.target_height)
        self.planned_foot_target[left].setZ(render, get_ground_z_pos(self.planned_foot_target[left].getX(render),
                                                                     self.planned_foot_target[left].getY(render), self.world,
                                                                     self.terrain_bullet_node))
        self.planned_foot_target[right].set_pos(self.pelvis_width / 4, step_dist, -self.target_height)
        self.planned_foot_target[right].setZ(render, get_ground_z_pos(self.planned_foot_target[right].getX(render),
                                                                      self.planned_foot_target[right].getY(render), self.world,
                                                                      self.terrain_bullet_node))

        # Update the walkcycle to determine if a step needs to be taken:
        update = cur_walk_dist
        update += ang_clamped * 0.5
        self.walk_cycle.updateTime(update)

        if self.walk_cycle.stepRequired[0]:
            self.walk_cycle.step(0)
            self.step_left = True
        if self.walk_cycle.stepRequired[1]:
            self.walk_cycle.step(1)
            self.step_right = True

        if self.step_left:
            diff = self.planned_foot_target[left].get_pos(render) - self.foot_target[left].get_pos()
            leg_move_dist = self.leg_movement_speed * globalClock.get_dt()
            if diff.length() < leg_move_dist:
                self.foot_target[left].set_pos(self.planned_foot_target[left].get_pos(render))
                self.step_left = False
            else:
                moved = self.foot_target[left].get_pos() + diff.normalized() * leg_move_dist
                self.foot_target[left].set_pos(moved)

        if self.step_right:
            diff = self.planned_foot_target[right].get_pos(render) - self.foot_target[right].get_pos()
            leg_move_dist = self.leg_movement_speed * globalClock.get_dt()
            if diff.length() < leg_move_dist:
                self.foot_target[right].set_pos(self.planned_foot_target[right].get_pos(render))
                self.step_right = False
            else:
                moved = self.foot_target[right].get_pos() + diff.normalized() * leg_move_dist
                self.foot_target[right].set_pos(moved)

        self.leg[left].updateIK()
        self.leg[right].updateIK()


    def turn_left(self):
        if abs(angle_diff(-self.lower_torso.getH(), self.desired_heading)) > 170:
            return
        self.desired_heading -= globalClock.get_dt() * 450
        self.desired_heading = normalize_angle(self.desired_heading)


    def turn_right(self):
        if abs(angle_diff(-self.lower_torso.getH(), self.desired_heading)) > 170:
            return
        self.desired_heading += globalClock.get_dt() * 450
        self.desired_heading = normalize_angle(self.desired_heading)


    def _update_heading(self):
        """Sets the angular velocity toward the desired heading.
        """
        diff = radians(angle_diff(-self.desired_heading, self.lower_torso.getH()))
        self.lower_torso.node().set_angular_velocity(Vec3(0, 0, -diff * 8))


    def _update_spine(self):
        velocity = self.get_body().node().get_linear_velocity()
        speed = Vec2(velocity.get_x(), velocity.get_y()).length()
        self.spine.set_p(max(-5, -speed / 1.5))


    def get_state_format(self):
        # https://docs.python.org/3/library/struct.html#format-characters
        return "ffeee"


    def get_compressed_state(self):
        """Gets the compressed state information
        """
        body = self.get_body()
        velocity = body.node().get_linear_velocity()
        return struct.pack(self.get_state_format(), body.get_x(), body.get_y(), body.get_h(),
                           velocity.get_x(), velocity.get_y())


    def set_state(self, x, y, heading, v_x, v_y):
        body = self.get_body()
        body.set_x(x)
        body.set_y(y)
        body.set_h(heading)
        body.node().set_linear_velocity(Vec3(v_x, v_y, body.node().get_linear_velocity().get_z()))


    def set_state_shifted(self, x, y, heading, v_x, v_y, shift_x, shift_y):
        self.set_state(x + shift_x, y + shift_y, heading, v_x, v_y)
