# -*- coding: utf-8 -*-

import math
import re
import random
import sys
import time
import cv2
import os
import numpy as np

if sys.version_info.major != 3:
    print('请使用Python3')
    exit(1)
try:
    from common import debug, config, screenshot, UnicodeStreamFilter
    from common.auto_adb import auto_adb
except Exception as ex:
    print(ex)
    print('请将脚本放在项目根目录中运行')
    print('请检查项目根目录中的 common 文件夹是否存在')
    exit(1)
adb = auto_adb()

# DEBUG 开关，需要调试的时候请改为 True，不需要调试的时候为 False
DEBUG_SWITCH = False
adb.test_device()
# Magic Number，不设置可能无法正常执行，请根据具体截图从上到下按需
# 设置，设置保存在 config 文件夹中
config = config.open_accordant_config()
screen_height = config['screen_height']
screen_width = config['screen_width']
under_game_score_y = config['under_game_score_y']
# 长按的时间系数，请自己根据实际情况调节
press_coefficient = config['press_coefficient']
# 二分之一的棋子底座高度，可能要调节
piece_base_height_1_2 = config['piece_base_height_1_2']
# 棋子的宽度，比截图中量到的稍微大一点比较安全，可能要调节
piece_body_width = config['piece_body_width']
# 图形中圆球的直径，可以利用系统自带画图工具，用直线测量像素，如果可以实现自动识别圆球直径，那么此处将可实现全自动。
head_diameter = config.get('head_diameter')
if head_diameter == None:
    density_str = adb.test_density()
    matches = re.search(r'\d+', density_str)
    density_val = int(matches.group(0))
    head_diameter = density_val / 8


def set_button_position(image):
    """
    将 swipe 设置为 `再来一局` 按钮的位置
    """
    global swipe_x1, swipe_y1, swipe_x2, swipe_y2
    try:
        swipe_x1 = config['swipe']['x1']
        swipe_y1 = config['swipe']['y1']
        swipe_x2 = config['swipe']['x2']
        swipe_y2 = config['swipe']['y2']
    except KeyError:       
        h, w, _ = image.shape
        left = int(w / 2)
        top = int(1584 * (h / 1920.0))
        left = int(random.uniform(left - 200, left + 200))
        top = int(random.uniform(top - 200, top + 200))  # 随机防 ban
        after_top = int(random.uniform(top - 200, top + 200))
        after_left = int(random.uniform(left - 200, left + 200))
        swipe_x1, swipe_y1, swipe_x2, swipe_y2 = left, top, after_left, after_top


def jump(piece_loc, board_loc):
    """
    跳跃一定的距离
    """
    # 计算程序长度与截图测得的距离的比例
    distance = math.sqrt((piece_loc[0] - board_loc[0]) ** 2 + (piece_loc[1] - board_loc[1]) ** 2)
    press_time = distance * press_coefficient
    press_time = max(press_time, 150)  # 设置 150ms 是最小的按压时间
    press_time = int(press_time)
    print('distance:{}, presstime:{}'.format(distance, press_time))

    cmd = 'shell input swipe {x1} {y1} {x2} {y2} {duration}'.format(
        x1=swipe_x1,
        y1=swipe_y1,
        x2=swipe_x2,
        y2=swipe_y2,
        duration=press_time
    )
    print(cmd)
    adb.run(cmd)
    return press_time

def get_piece_board_loc(screen_shot, template):
    """
    1.使用opencv模板匹配，识别跳棋位置
    2.识别下一个方块的位置
    """
    h, w, _ = screen_shot.shape
    template_h, template_w, _ = template.shape
    
    # 1.识别跳棋
    # 使用标准相关系数匹配,1表示完美匹配,-1表示糟糕的匹配,0表示没有任何相关性
    result = cv2.matchTemplate(screen_shot, template, cv2.TM_CCOEFF_NORMED)
    # 使用函数minMaxLoc,确定匹配结果矩阵的最大值和最小值(val)，以及它们的位置(loc)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    piece_top_left = max_loc
    piece_bottom_right = (piece_top_left[0]+template_w, piece_top_left[1]+template_h)
    # 得到小跳棋的中心位置参数
    piece_x = int(piece_top_left[0] + template_w * 0.5)
    piece_y = int(piece_top_left[1] + template_h * 0.9)
    piece_loc = (piece_x, piece_y)
    
    
    # 2.识别棋盘
    # 缩小搜索范围
    # + - template_w是为了避开搜索棋子位置，以免造成干扰
    start_end_x = (0, 0)
    start_end_y = (int(h / 3), int(h * 2 / 3))
    if piece_loc[0] < w / 2:
        start_end_x = (piece_loc[0] + int(template_w / 2), w)
    else:
        start_end_x = (0, piece_loc[0] - int(template_w / 2))
    

    # pdb.set_trace()
    # 定位方块顶点位置 从上往下粗略搜索，确定大致位置 步长为50
    start_x = 0
    start_y = 0 
    # i表示行，j表示列
    for i in range(start_end_y[0], start_end_y[1], 50):
        last_pixel = screen_shot[i, 0]
        for j in range(start_end_x[0], start_end_x[1]):
            a = screen_shot[i, j].astype(np.int)
            b = last_pixel.astype(np.int)
            if sum(abs(a - b)) >= 30:
                start_y = i - 49
                start_x = j
                break
        if start_x or start_y:
            break    
    # pdb.set_trace()
    # 精细搜索
    # 寻找同一横线上的多个点，然后取平均值
    # 只记录j值即可，因为同一横线上的i值相同
    board_top_loc = (0, 0)
    last_pixel = screen_shot[start_y, start_x]
    points = []
    for i in range(start_y, start_y+50):
        for j in range(start_x, start_end_x[1]):
            a = screen_shot[i, j].astype(np.int)
            b = last_pixel.astype(np.int)
            if sum(abs(a - b)) >= 30:
                points.append(j)
        if points:
            break 
    # pdb.set_trace()
    board_top_loc = (int(sum(points) / len(points)), i)
    
    board_x = board_top_loc[0]
    # pdb.set_trace()
    # 计算对称中心， 依据固定角度算出y值
    center_x = w / 2 + (24 / screen_width) * w
    center_y = h / 2 + (17 / screen_height) * h
    if piece_x > center_x:
        board_y = round((25.5 / 43.5) * (board_x - center_x) + center_y)
    else:
        board_y = round(-(25.5 / 43.5) * (board_x - center_x) + center_y)

    if not all((board_x, board_y)):
        return 0, 0, 0, 0, 0 
    
    board_loc = (board_x, board_y)
    # pdb.set_trace()
    return piece_top_left, piece_bottom_right, piece_loc, board_loc   

def yes_or_no():
    """
    检查是否已经为启动程序做好了准备
    """
    while True:
        yes_or_no = str(input('请确保手机打开了 ADB 并连接了电脑，'
                              '然后打开跳一跳并【开始游戏】后再用本程序，确定开始？[y/n]:'))
        if yes_or_no == 'y':
            break
        elif yes_or_no == 'n':
            print('谢谢使用', end='')
            exit(0)
        else:
            print('请重新输入')


def main():
    """
    主函数
    """
    print('激活窗口并按 CONTROL + C 组合键退出')
    if DEBUG_SWITCH:
        print('DEBUG模式已开启')
    else:
        print('DEBUG模式已关闭')
    debug.dump_device_info()
    screenshot.check_screenshot()

    i, next_rest, next_rest_time = (0, random.randrange(3, 10),
                                    random.randrange(5, 10))
    while True:
        image = screenshot.pull_screenshot()
        work_path = sys.path[0]
        template = cv2.imread(os.path.join(work_path, 'piece.png'))
        # 获取棋子和 board 的位置
        piece_top_left, piece_bottom_right, piece_loc, board_loc = get_piece_board_loc(image, template)
        ts = int(time.time())
        print("\ntime:{}, piece_loc:{}, board_loc:{}".format(ts, piece_loc, board_loc))
        set_button_position(image)
        jump(piece_loc, board_loc)
        if DEBUG_SWITCH:
            debug.save_debug_screenshot(ts, image, piece_top_left, piece_bottom_right,
                                        piece_loc, board_loc)
            # debug.backup_screenshot(ts)
        i += 1
        if i == next_rest:
            print('已经连续打了 {} 下，休息 {}秒'.format(i, next_rest_time))
            for j in range(next_rest_time):
                sys.stdout.write('\r程序将在 {}秒 后继续'.format(next_rest_time - j))
                sys.stdout.flush()
                time.sleep(1)
            print('\n继续')
            i, next_rest, next_rest_time = (0, random.randrange(30, 100),
                                            random.randrange(10, 60))
        # 为了保证截图的时候应落稳了，多延迟一会儿，随机值防 ban
        time.sleep(random.uniform(1.2, 1.4))


if __name__ == '__main__':
    try:
        yes_or_no()
        main()
    except KeyboardInterrupt:
        adb.run('kill-server')
        print('\n谢谢使用', end='')
        exit(0)
