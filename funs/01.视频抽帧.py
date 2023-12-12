# -*- coding: utf-8 -*-
# @Time    : 2023/12/6 23:17
# @QQ  : 2942581284
# @File    : 01.视频抽帧.py
import cv2
import os

def get_video_frames(video_path=r"D:\program\剪映\导出\如何给我们的PyQt6程序制作一个炫酷的充值按钮.mp4",
					 tmp_imgs_path='tmp_imgs'):
	tmp_folder_path, file_extension = os.path.splitext(os.path.basename(video_path))
	folder_path=os.path.join(tmp_imgs_path, tmp_folder_path)
	if not os.path.exists(folder_path):
		os.makedirs(folder_path)
	# 打开视频文件
	cap = cv2.VideoCapture(video_path)
	# 检查视频是否成功打开
	if not cap.isOpened():
		print("无法打开视频文件")
	else:
		# 获取视频帧数
		total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
		print(f"视频总帧数: {total_frames}")
		frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
		print(f"视频帧率: {frame_rate} fps")
		# 设置帧间隔，每秒抽取一帧,1秒抽取1帧
		frame_interval = frame_rate // 1
		# 循环遍历视频的每一帧并保存为图像
		frame_count = 0
		while True:
			ret, frame = cap.read()
			if not ret:
				break
			if frame_count % frame_interval == 0:
				image_filename = f"frame_{frame_count:06d}.png"
				image_save_path=os.path.join(folder_path,image_filename)
				cv2.imencode(".png", frame)[1].tofile(image_save_path)
				print(f"保存图像:{image_filename},视频抽帧进度:{frame_count//frame_interval}/{total_frames//frame_interval}:{frame_count}/{total_frames}")
			frame_count += 1
	cap.release()

get_video_frames()