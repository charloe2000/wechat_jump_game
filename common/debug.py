# -*- coding: utf-8 -*-
"""
这是debug的代码，当DEBUG_SWITCH开关开启的时候，会将各种信息存在本地，方便检查故障
"""
import os
import sys
import shutil
import math
import platform
import cv2

if platform.system() == 'Windows':
    os.chdir(os.getcwd().replace('\\common', ''))
    path_split = "\\"
else:
    os.chdir(os.getcwd().replace('/common', ''))
    path_split = '/'
# from common import ai
try:
    from common.auto_adb import auto_adb
except ImportError as ex:
    print(ex)
    print('请将脚本放在项目根目录中运行')
    print('请检查项目根目录中的 common 文件夹是否存在')
    exit(1)
screenshot_backup_dir = 'screenshot_backups'


def make_debug_dir(screenshot_backup_dir):
    """
    创建备份文件夹
    """
    if not os.path.isdir(screenshot_backup_dir):
        os.mkdir(screenshot_backup_dir)
        

def save_debug_screenshot(ts, image, piece_top_left, piece_bottom_right, piece_loc, board_loc):
    """
    对 debug 图片加上详细的注释
    
    """
    make_debug_dir(screenshot_backup_dir)
    cv2.rectangle(image, piece_top_left, piece_bottom_right, (0, 255, 0), 5)
    cv2.circle(image, piece_loc, 10, (0, 0, 255), -1)
    cv2.circle(image, board_loc, 10, (0, 0, 255), -1)
    cv2.line(image, piece_loc, board_loc, (255, 0, 0), 5)
    cv2.imwrite(os.path.join(sys.path[0], screenshot_backup_dir,
                         '#' + str(ts) + '.png'), image)


def dump_device_info():
    """
    显示设备信息
    """
    adb = auto_adb()
    size_str = adb.get_screen()
    device_str = adb.test_device_detail()
    phone_os_str = adb.test_device_os()
    density_str = adb.test_density()
    print("""**********
Screen: {size}
Density: {dpi}
Device: {device}
Phone OS: {phone_os}
Host OS: {host_os}
Python: {python}
**********""".format(
        size=size_str.replace('\n', ''),
        dpi=density_str.replace('\n', ''),
        device=device_str.replace('\n', ''),
        phone_os=phone_os_str.replace('\n', ''),
        host_os=sys.platform,
        python=sys.version
    ))
