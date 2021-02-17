from math import floor

# TODO: compare speed to angleDeg in Panda's Vec3
def angleDiff(angle1, angle2):
    return (angle2 - angle1 + 180) % 360 - 180
