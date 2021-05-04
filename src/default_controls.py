from math import radians

from direct.showbase.InputStateGlobal import inputState
from src.inverse_kinematics.Utils import createAxes

dxdy_to_angle = [[radians(45), radians(90), radians(135)], [radians(0), -999, radians(180)], [radians(-45), radians(-90), radians(-135)]]


def setup_controls(player):
    inputState.watch_with_modifiers('forward', 'w')
    inputState.watch_with_modifiers('left', 'a')
    inputState.watch_with_modifiers('backward', 's')
    inputState.watch_with_modifiers('right', 'd')
    inputState.watch_with_modifiers('turnleft', 'q')
    inputState.watch_with_modifiers('turnright', 'e')
    inputState.watch_with_modifiers('speedup', '+')
    inputState.watch_with_modifiers('speeddown', '-')


def interpret_controls(target, stand_still=False, move_weapon_target=True):
    if stand_still:
        target.stand_still()
        return

    dx = dy = 1
    if inputState.is_set('forward'):
        dy -= 1
    if inputState.is_set('backward'):
        dy += 1
    if inputState.is_set('left'):
        dx -= 1
    if inputState.is_set('right'):
        dx += 1
    direction = dxdy_to_angle[dy][dx]

    if inputState.is_set('turnleft'):
        target.turn_left()
    if inputState.is_set('turnright'):
        target.turn_right()

    if inputState.is_set('speedup'):
        target.speed_up()
    if inputState.is_set('speeddown'):
        target.slow_down()

    if direction > -900:
        target.walk_in_dir(direction)
    else:
        target.stand_still()

    if base.mouseWatcherNode.has_mouse() and move_weapon_target:
        x = min(max(-1, base.mouseWatcherNode.get_mouse_x()), 1)
        y = -min(max(-1, base.mouseWatcherNode.get_mouse_y()), 1)
        '''
        x = min(max(-1, base.mouseWatcherNode.get_mouse_x()), 1)*2
        y = -min(max(-1, base.mouseWatcherNode.get_mouse_y()), 1)*2
        # Some inspiration taken from a hemisphere's equation when solved for Z
        pows = pow(x, 2)+pow(y, 2)
        z = 1 - pow(pows, 0.5)

        target.swing_arm(1, x * 2, y * 2, z * 2)
        '''
        target.swing_arm(1, x, y)
