import random
from src.InverseKinematics.IKChain import IKChain
from src.InverseKinematics.WalkCycle import WalkCycle
from src.InverseKinematics.Utils import *
from src.shapes import create_rounded_box, create_sphere
from src.humanoid_arm import HumanoidArm
from src.utils import angle_diff, normalize_angle, get_ground_Z_pos, get_object_ground_Z_pos
from math import cos, sin, radians, degrees
from panda3d.bullet import BulletSphereShape, BulletConeTwistConstraint, BulletGenericConstraint

class Humanoid():
    """
    A class for humanoid creatures. 
    """
    def __init__( self, render, world, terrain_bullet_node, x, y, height=1.7, start_heading=Vec3(0,0,0), debug = False, debug_text_node = None ):
        self.render = render
        self.world = world
        self.terrain_bullet_node = terrain_bullet_node
        self.debug = debug

        # Initialize body proportions
        self.height = height
        self.head_height = self.height/7
        self.chest_width = 0.38
        self.pelvis_width = 0.38
        self.lower_torso_height = 1.5*(self.height/7)
        self.chest_height = 1.5*(self.height/7)

        self.leg_height = self.height - self.head_height - self.lower_torso_height - self.chest_height
        self.thigh_length = self.leg_height*59/109
        thigh_diameter = self.pelvis_width/2-0.01
        self.lower_leg_length = self.leg_height*40/109
        lower_leg_diameter = (self.pelvis_width/2-0.01)*self.leg_height
        self.foot_height = self.leg_height - self.thigh_length - self.lower_leg_length
        self.foot_length = lower_leg_diameter*2.2

        self.arm_height = self.leg_height*1
        self.upper_arm_length = self.arm_height*50/100
        upper_arm_diameter = self.chest_width/3-0.01
        self.forearm_length = self.arm_height*50/100
        forearm_diameter = (self.chest_width/3-0.01)*self.arm_height

        self.target_height = self.leg_height + self.lower_torso_height/2

        # Control node and the whole body collision box
        self.lower_torso = create_rounded_box(self.render, self.chest_width, 0.2, self.chest_height)
        start_position = Vec3(x,y,self.target_height+get_ground_Z_pos(x, y, self.world, self.terrain_bullet_node))
        self.lower_torso.set_pos_hpr(start_position, start_heading)
        self.lower_torso.node().set_mass(30.0)
        self.lower_torso.node().set_angular_factor(Vec3(0,0,0.1))
        self.lower_torso.node().set_linear_damping(0.8)
        self.lower_torso.node().set_angular_sleep_threshold(0) # Sleep would freeze the whole character if still
        self.lower_torso.set_collide_mask(BitMask32.bit(3))
        self.world.attach(self.lower_torso.node())

        self.chest = create_rounded_box(self.render, self.chest_width, 0.2, self.chest_height)
        self.chest.node().set_mass(30.0)
        self.chest.node().set_angular_factor(Vec3(0.15,0.05,0.1))
        self.chest.node().set_linear_damping(0.5)
        self.chest.set_collide_mask(BitMask32.bit(3))
        self.world.attach(self.chest.node())
        self.chest.node().set_angular_sleep_threshold(0.05)

        frame_a = TransformState.make_pos_hpr(Point3(0, 0, -self.chest_height/2), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.lower_torso_height/2), Vec3(0, 0, 0))

        swing1 = 10 # leaning forward/backward degrees
        swing2 = 5 # leaning side to side degrees
        twist = 30 # degrees

        cs = BulletConeTwistConstraint(self.chest.node(), self.lower_torso.node(), frame_a, frame_b)
        cs.set_debug_draw_size(0.5)
        cs.set_limit(twist, swing2, swing1, softness=0.1, bias=1.0, relaxation=1.0)
        world.attach_constraint(cs, linked_collision=True)


        self.left_arm = HumanoidArm(self.chest, self.world, self.arm_height, self.chest_width/3-0.01, (self.chest_width/3-0.01)*self.arm_height, False, start_position, start_heading)

        frame_a = TransformState.make_pos_hpr(Point3(-self.chest_width/2-self.left_arm.upper_arm_diameter/2, 0, self.chest_height/2-self.left_arm.upper_arm_diameter/8), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.left_arm.upper_arm_length/2), Vec3(0, -90, 0))

        self.left_arm_constraint = BulletGenericConstraint(self.chest.node(), self.left_arm.upper_arm.node(), frame_a, frame_b, True)
        self.left_arm_constraint.set_debug_draw_size(0.5)
        self.left_arm_constraint.set_angular_limit(0, -95, 135) # Front and back
        self.left_arm_constraint.set_angular_limit(1, 0, 0)     # Rotation, handled in the elbow joint because here it glitches.
        self.left_arm_constraint.set_angular_limit(2, -120, 35) # Left and right
        self.left_arm.upper_arm.node().set_angular_factor(Vec3(0.2,0.2,0.2))
        self.world.attach_constraint(self.left_arm_constraint, linked_collision=True)


        self.right_arm = HumanoidArm(self.render, self.world, self.arm_height, self.chest_width/3-0.01, (self.chest_width/3-0.01)*self.arm_height, True, start_position, start_heading)

        frame_a = TransformState.make_pos_hpr(Point3(self.chest_width/2+self.right_arm.upper_arm_diameter/2, 0, self.chest_height/2-self.right_arm.upper_arm_diameter/8), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0, 0, self.right_arm.upper_arm_length/2), Vec3(0, -90, 0))

        self.right_arm_constraint = BulletGenericConstraint(self.chest.node(), self.right_arm.upper_arm.node(), frame_a, frame_b, True)
        self.right_arm_constraint.set_debug_draw_size(0.5)
        self.right_arm_constraint.set_angular_limit(0, -95, 135) # Front and back
        self.right_arm_constraint.set_angular_limit(1, 0, 0)     # Rotation, handled in the elbow joint because here it glitches.
        self.right_arm_constraint.set_angular_limit(2, -35, 120) # Left and right
        self.right_arm.upper_arm.node().set_angular_factor(Vec3(0.2,0.2,0.2))
        self.world.attach_constraint(self.right_arm_constraint, linked_collision=True)


        self.head = create_sphere(self.render, self.head_height)
        self.head.node().set_mass(3.0)
        self.head.set_collide_mask(BitMask32.bit(3))
        self.world.attach(self.head.node())

        frame_a = TransformState.make_pos_hpr(Point3(0,0,self.head_height/2), Vec3(0, 0, 0))
        frame_b = TransformState.make_pos_hpr(Point3(0,0,-self.chest_height/2), Vec3(0, 0, 0))

        self.neck = BulletGenericConstraint(self.chest.node(), self.head.node(), frame_a, frame_b, True)

        self.neck.set_debug_draw_size(0.5)
        self.neck.set_angular_limit(0, -10, 10)
        self.neck.set_angular_limit(1, 0, 0)
        self.neck.set_angular_limit(2, -10, 10)
        self.world.attach_constraint(self.neck, linked_collision=True)

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

#            hip = self.lower_torso.attach_new_node("Hip")
#            hip.set_pos(Vec3(horizontal_placement*self.pelvis_width/4,0,-self.lower_torso_height/2))

            # Place the hip
            legRootLeft = self.lower_torso.attach_new_node( "LegRootLeft" )
            legRootLeft.setPosHpr( Vec3(horizontal_placement*self.pelvis_width/4,0,-self.lower_torso_height/2), Vec3(0, 0, 0) )
            self.leg.append(IKChain( legRootLeft ))

            # Hip:
            self.thigh.append(self.leg[i].addBone( offset=LVector3f.zero(),
                    minAng = math.pi/2-math.pi*0.2,
                    maxAng = math.pi/2+math.pi*0.2,
                    rotAxis = None
                    ))

            # Knee:
            lower_leg.append(self.leg[i].addBone( offset=LVector3f.unitY()*self.thigh_length,
                    minAng = -math.pi*0.7,
                    maxAng = 0,
                    rotAxis = LVector3f.unitZ(),
                    parentBone = self.thigh[i]
                    ))

            # End of the lower leg:
            bone = self.leg[i].addBone( offset=LVector3f.unitY()*self.lower_leg_length,
                    minAng = 0,
                    maxAng = math.pi*0.6,
                    rotAxis = None,
                    parentBone = lower_leg[i]
                    )

            # We want a fixed 90° angle between the hip node and the thigh, so
            # rotate down:
#            bone = self.leg[i].addBone( offset=LVector3f.zero(),
#                    minAng = -math.pi*0.5,
#                    maxAng = -math.pi*0.5,
#                    rotAxis = LVector3f.unitX(),
#                    parentBone = bone
#                    )

            # Thigh:
#            thigh.append(self.leg[i].addBone( offset=Vec3(0,self.thigh_length,0),
#                    minAng = 0,
#                    maxAng = math.pi*0.7,
#                    rotAxis = None,
#                    parentBone = bone
#                    ))
            # Shin:
#            lower_leg.append(self.leg[i].addBone( offset=Vec3(0,-self.lower_leg_length,0),
#                    minAng = 0,
#                    maxAng = 0,
#                    rotAxis = None,
#                    parentBone = thigh[i]
#                    ))

            '''
            thigh.append(self.leg[i].addBone( offset=Vec3(0,0,-self.thigh_length),
#                    minAng = -math.pi*0.25,
#                    maxAng = math.pi*0.25,
                    minAng = 0,
                    maxAng = 0,
                    rotAxis = None,
                    ))

            lower_leg.append(self.leg[i].addBone( offset=Vec3(0,0,-self.lower_leg_length*1.5),
                    minAng = -math.pi*0.5,
#                    minAng = 0,
                    maxAng = math.pi*0.5,
                    rotAxis = None,
                    parentBone = thigh[i]
                    ))
            '''

            self.leg[i].finalize()
            self.foot.append(bone.ikNode.attach_new_node("Foot"))
            self.foot[i].set_pos_hpr(Vec3(0,lower_leg_diameter/2-self.foot_height/2,lower_leg_diameter/2), Vec3(0,-90,0))

            if self.debug:
                self.leg[i].debugDisplay()

            self.leg[i].updateIK()


            #################################################
            # Foot targets:

            # Set up a target that the foot should reach:
            self.foot_target.append(self.render.attach_new_node("FootTarget"))
            self.foot_target[i].setZ(self.target_height+get_object_ground_Z_pos(self.foot_target[i], self.world, self.terrain_bullet_node))
            self.leg[i].setTarget( self.foot_target[i] )

            # Set up nodes which stay (rigidly) infront of the body, on the floor.
            # Whenever a leg needs to take a step, the target will be placed on this position:
            self.planned_foot_target.append(self.lower_torso.attach_new_node( "PlannedFootTarget" ))
            step_dist = 0.35
            self.planned_foot_target[i].set_pos( horizontal_placement*self.pelvis_width/4, step_dist, -self.target_height )

            if self.debug:
                geom = createAxes( 0.2 )
                self.foot_target[i].attach_new_node( geom )
                self.planned_foot_target[i].attach_new_node( geom )


        # Add visuals to the bones. These MUST be after finalize().

        for i in range(len(self.leg)):
            visual = loader.load_model("3d-assets/unit_cylinder.bam")
            visual.set_scale(Vec3(thigh_diameter, thigh_diameter, self.thigh_length))
            visual.reparent_to(self.thigh[i].ikNode)
            visual.set_pos( (visual.get_pos() + lower_leg[i].offset)/2 )
            visual.set_hpr( 0, -90, 0 )

            visual = loader.load_model("3d-assets/unit_cylinder.bam")
            visual.set_scale(Vec3(lower_leg_diameter, lower_leg_diameter, self.lower_leg_length))
            visual.reparent_to(lower_leg[i].ikNode)
            visual.set_pos( (visual.get_pos() + bone.offset)/2 )
            visual.set_hpr( 0, -90, 0 )

            footVisual = loader.load_model("3d-assets/unit_cube.bam")
            footVisual.reparent_to(self.foot[i])
            footVisual.set_scale(Vec3(lower_leg_diameter, self.foot_length, self.foot_height))


        self.head.set_pos_hpr(start_position, start_heading)
        self.chest.set_pos_hpr(start_position, start_heading)

        # To reduce the harmful effects of gravity on custom ground collision, have a net zero gravity
        counteract_mass = self.left_arm.get_mass() + self.right_arm.get_mass()
        self.head.node().set_gravity(Vec3(0, 0, 0))
        self.lower_torso.node().set_gravity(Vec3(0, 0, 9.81*counteract_mass/self.lower_torso.node().get_mass()))
        self.chest.node().set_gravity(Vec3(0, 0, 0))

        self.leg_movement_speed = self.walk_speed*3

        self.step_left = False
        self.step_right = False
        
        self.walk_cycle = WalkCycle( 2, 0.75 )
        self.desired_heading = self.lower_torso.getH()


    def speed_up( self ):
        self.walk_speed += 0.1
        self.walk_speed = min(self.walk_speed, 9)
        self.leg_movement_speed = self.walk_speed*3

    def slow_down( self ):
        self.walk_speed -= 0.1
        self.walk_speed = max(self.walk_speed, 0)
        self.leg_movement_speed = self.walk_speed*3


    def get_correct_Z_velocity(self, current_Z_pos=None):
        # Too high and you'll get massive jittering at sharp points in the terrain physics node
        vector = self.lower_torso.node().get_linear_velocity()
        # Determine some Z change that is allowed. It's got to be low enough to reduce jitter.
        max_Z_change = 4*globalClock.get_dt()*min(self.walk_speed, 4*Vec3(vector.getX(), vector.getY(), 0).length())
        if current_Z_pos:
            return -min(max_Z_change,max(current_Z_pos,-max_Z_change))/globalClock.get_dt()
        return -min(max_Z_change,max(self.get_feet_averaged_ground_Z_pos(),-max_Z_change))/globalClock.get_dt()


    def get_feet_averaged_ground_Z_pos(self, offset_x=0, offset_y=0):
        average_x = 0
        average_y = 0
        average_z = 0
        for foot in self.foot:
            average_x += foot.getX(self.render)
            average_y += foot.getY(self.render)
            average_z += foot.getZ(self.render)-self.foot_height/2
        average_x /= len(self.foot)
        average_y /= len(self.foot)
        average_z /= len(self.foot)
        average_z -= get_ground_Z_pos(average_x+offset_x, average_y+offset_y, self.world, self.terrain_bullet_node)
        return average_z


    def stand_still(self):
        self.walk_in_dir(self.lower_torso.getH(), decelerate=True)


    def walk_in_dir( self, angle=0, visuals=True, decelerate=False ):
#        for i in range(len(self.leg)):
#            self.thigh[i].ikNode.setR(0)
        if not decelerate:
            math_angle = radians(angle+90)
            diff = Vec3(-cos(math_angle),sin(math_angle),0)
            diff_n = diff.normalized()
            step = diff_n*self.walk_speed

        current_Z_pos = self.get_feet_averaged_ground_Z_pos()
        preliminary_Z_velocity = self.get_correct_Z_velocity(current_Z_pos)
        if decelerate:
            new_vector = Vec3(self.lower_torso.node().get_linear_velocity().getX(), self.lower_torso.node().get_linear_velocity().getY(), preliminary_Z_velocity)
        else:
            ca = cos(radians(self.lower_torso.getH()))
            sa = sin(radians(self.lower_torso.getH()))
            new_vector = Vec3(ca*step.getX() - sa*step.getY(), sa*step.getX() + ca*step.getY(), preliminary_Z_velocity)
        z_diff = current_Z_pos - self.get_feet_averaged_ground_Z_pos(offset_x=new_vector.getX()*0.01, offset_y=new_vector.getY()*0.01)

        mult_min = 0.01
        if z_diff > mult_min:
            mult_max = 0.02
            mult = ((1/mult_max)*(mult_max-mult_min - (min(mult_max,z_diff)-mult_min)))
            self.lower_torso.node().set_linear_velocity(Vec3(new_vector.getX()*mult, new_vector.getY()*mult, preliminary_Z_velocity))
            if z_diff >= mult_max:
                return
        else:
            self.lower_torso.node().set_linear_velocity(new_vector)

        # Negligible speed; assume we've come to a halt and save on resources
        if self.lower_torso.node().get_linear_velocity().length() < 0.2 and abs(self.lower_torso.node().get_angular_velocity().getZ()) < 0.1:
            self.lower_torso.node().set_linear_velocity(Vec3(0,0,self.lower_torso.node().get_linear_velocity().getZ()))
            return

        if visuals:
            # Calculate how far we've walked this frame:
            cur_walk_dist = self.lower_torso.node().get_linear_velocity().length()*globalClock.get_dt()
            self._walking_visuals( cur_walk_dist, 0 )


    def _walking_visuals( self, cur_walk_dist, ang_clamped ):
        #############################
        # Update legs:

        # Move planned foot target further forward (longer steps) when character is
        # walking faster:
        step_dist = cur_walk_dist*0.1/globalClock.get_dt()
        left = 0
        right = 1
        self.planned_foot_target[left].set_pos( -self.pelvis_width/4, step_dist, -self.target_height )
        self.planned_foot_target[left].setZ( self.render, get_ground_Z_pos(self.planned_foot_target[left].getX(self.render), self.planned_foot_target[left].getY(self.render), self.world, self.terrain_bullet_node) )
        self.planned_foot_target[right].set_pos( self.pelvis_width/4, step_dist, -self.target_height )
        self.planned_foot_target[right].setZ( self.render, get_ground_Z_pos(self.planned_foot_target[right].getX(self.render), self.planned_foot_target[right].getY(self.render), self.world, self.terrain_bullet_node) )

        # Update the walkcycle to determine if a step needs to be taken:
        update = cur_walk_dist
        update += ang_clamped*0.5
        self.walk_cycle.updateTime( update )

        if self.walk_cycle.stepRequired[0]:
            self.walk_cycle.step( 0 )
            self.step_left = True
        if self.walk_cycle.stepRequired[1]:
            self.walk_cycle.step( 1 )
            self.step_right = True

        if self.step_left:
            diff = self.planned_foot_target[left].get_pos(self.render) - self.foot_target[left].get_pos()
            leg_move_dist = self.leg_movement_speed*globalClock.get_dt()
            if diff.length() < leg_move_dist:
                self.foot_target[left].set_pos( self.planned_foot_target[left].get_pos( self.render ) )
                self.step_left = False
            else:
                moved = self.foot_target[left].get_pos() + diff.normalized()*leg_move_dist
                self.foot_target[left].set_pos( moved )

        if self.step_right:
            diff = self.planned_foot_target[right].get_pos(self.render) - self.foot_target[right].get_pos()
            leg_move_dist = self.leg_movement_speed*globalClock.get_dt()
            if diff.length() < leg_move_dist:
                self.foot_target[right].set_pos( self.planned_foot_target[right].get_pos( self.render ) )
                self.step_right = False
            else:
                moved = self.foot_target[right].get_pos() + diff.normalized()*leg_move_dist
                self.foot_target[right].set_pos( moved )

        self.leg[left].updateIK()
        self.leg[right].updateIK()


    def turn_left(self):
        if abs(angle_diff(-self.lower_torso.getH(), self.desired_heading)) > 170:
            return
        self.desired_heading -= globalClock.get_dt()*450
        self.desired_heading = normalize_angle(self.desired_heading)
        self.update_heading()

    def turn_right(self):
        if abs(angle_diff(-self.lower_torso.getH(), self.desired_heading)) > 170:
            return
        self.desired_heading += globalClock.get_dt()*450
        self.desired_heading = normalize_angle(self.desired_heading)
        self.update_heading()

    def update_heading(self):
        diff = radians(angle_diff(-self.desired_heading, self.lower_torso.getH()))
        self.lower_torso.node().set_angular_velocity(Vec3(0,0,-diff*8))
