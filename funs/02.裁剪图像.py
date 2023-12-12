# -*- coding: utf-8 -*-
# @Time    : 2023/12/6 23:17
# @QQ  : 2942581284
# @File    : 02.裁剪图像.py
import os
import cv2
import numpy as np


def cv_imread(file_path):
    cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), -1)
    return cv_img


# imgurl='测试.jpg'
# img1 = cv_imread(imgurl)
# cv2.imencode('.jpg', img1 )[1].tofile(imgurl)

def cut_zimu_from_img(
        imgs_path=r'D:\文件夹\github_\myshare_github\Python-Project-Pro\视频文案提取-OCR字幕识别\tmp_imgs\【PyQtPySide界面美化】qt-material极简上手！'):
    zimu_folder_name = os.path.basename(imgs_path) + '-字幕'
    zimu_path = os.path.join(os.path.dirname(imgs_path), zimu_folder_name)
    if not os.path.exists(zimu_path):
        os.makedirs(zimu_path)
    # 获取文件夹中的所有图片文件
    image_files = [f for f in os.listdir(imgs_path)]
    # 定义裁剪区域的坐标 (x, y, width, height)
    height_min = 1800
    height_max = 1950
    width = 3800
    crop_area = (0, height_min, width, height_max - height_min)
    # 循环处理每个图片文件
    for image_file in image_files:
        # 拼接图片文件的完整路径
        image_path = os.path.normpath(os.path.join(imgs_path, image_file))

        print(image_path)
        # 读取图片
        image = cv_imread(image_path)
        # image = cv2.imread(image_path)
        if image is not None:
            # 裁剪图片
            x, y, w, h = crop_area
            cropped_image = image[y:y + h, x:x + w]
            # 保存裁剪后的图片
            output_file = os.path.join(zimu_path, f"cropped_{image_file}")
            cv2.imencode(".png", cropped_image)[1].tofile(output_file)
            print(f"已保存裁剪后的图片：{output_file}")
        else:
            print(f"无法读取图片：{image_path}")

cut_zimu_from_img()