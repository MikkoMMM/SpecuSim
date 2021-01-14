# This is a simple command line utility to test out the orientation estimation for a Wiimote

from fusion import Fusion
import cwiid
import time
from deltat import DeltaT
from math import cos, degrees, radians

def timediff(time1, time2):
    return (time1-time2)


# This part is for connecting the Wii Remote.
print("Press 1+2 on your Wiimote now...")
wiimote = cwiid.Wiimote()
time.sleep(1)
wiimote.rpt_mode = cwiid.RPT_BTN | cwiid.RPT_ACC | cwiid.RPT_MOTIONPLUS | cwiid.RPT_IR
wiimote.enable(cwiid.FLAG_MOTIONPLUS)
time.sleep(1)

fuse = Fusion(timediff)

deltat = DeltaT(timediff)
count = 0
heading = 0
while True:
    # This ordering of values seems to correspond most closely to the order yaw, pitch, and then roll. Though, the "yaw" doesn't give intuitive values.
    # Tilting the Wiimote upward in pitch, the ['acc'][1] gets lower. Tilting it down, the ['acc'][1] gets higher.
    # Rolling it counterclockwise, the ['acc'][0] gets lower. Rolling clockwise, the ['acc'][0] value gets higher.
    accel = (wiimote.state['acc'][0]-123.15, wiimote.state['acc'][1]-123.06, wiimote.state['acc'][2]-123.1)

    angle_rates = wiimote.state['motionplus']['angle_rate']

    # This ordering of values seems to correspond most closely to the order yaw, pitch, and then roll.
    # By tilting the Wiimote upward in pitch, the angle_rates[0] gets momentarily lower. Downward pitch gets it to go higher.
    # By rolling the Wiimote counterclockwise, the angle_rates[1] gets momentarily higher. Rolling it clockwise, it gets lower.
    # By swaying the Wiimote toward the left in yaw, the angle_rates[2] gets momentarily higher. Swaying it toward the right, it gets lower.

    # Explanation for the dividing by low_speed times something bit:
    # When low_speed is 1, then 20 represents turning at about 1 degree per second. So divide by 20 to get the degrees per second.
    # At high speed (Low speed bit = 0) 20 represents turning at about 5 degree per second. So divide by 4 to get the degrees per second.
    # Source: http://arduino-projects4u.com/wii-motion-plus/

    # The -7945, -8115 and -7964 calibrate the values so that for me the gyro values will be close to zero when the Wii Remote is resting on the table.
    gyro = (
        (angle_rates[0]-8119.34)/(4.0+wiimote.state['motionplus']['low_speed'][0]*16),
        (angle_rates[1]-7943.68)/(4.0+wiimote.state['motionplus']['low_speed'][1]*16),
        (angle_rates[2]-7959.64)/(4.0+wiimote.state['motionplus']['low_speed'][2]*16),
    )
    fuse.update_nomag(accel, gyro, time.time())
    deltag2 = deltat(time.time()) * radians(gyro[2])
    heading += deltag2
    
    if count % 50 == 0:
        print()
        print("Raw accelerometer values: ", accel, ". Raw gyro values: ", gyro)
        if 'ir_src' in wiimote.state:
            ir1 = wiimote.state['ir_src'][0]
            ir2 = wiimote.state['ir_src'][1]
            # Range: X 0-1023, Y 0-767
            if wiimote.state['ir_src'][0]:
                print("IR 1: ", ir1)
            if wiimote.state['ir_src'][1]:
                print("IR 2: ", ir2)
            if wiimote.state['ir_src'][0] and wiimote.state['ir_src'][1]:
                heading = 0
        print("Heading, Roll, Pitch: ", degrees(heading), "{:7.3f} {:7.3f}".format(fuse.pitch, fuse.roll))
    count += 1
