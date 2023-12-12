# -*- coding: utf-8 -*-
# @Time    : 2023/12/6 20:25
# @QQ  : 2942581284
# @File    : 提取中间字幕.py
import os
import json

def extract_zimu_from_file(file):
    with open(file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    zimu_width = 3800
    if data:
        # print(data)
        ocrResult=data['ocrResult']
        if ocrResult:
            ocrResult.sort(key=lambda x:-1*(x['location']['right']-x['location']['left']))
            center=ocrResult[0]['location']['left']+ocrResult[0]['location']['right']
            if abs(center - zimu_width) < 100:
                print(ocrResult[0]['text'])
                return ocrResult[0]['text']
    else:
        return False

def connect_center_result(file_path=r'D:\文件夹\github_\myshare_github\Python-Project-Pro\视频文案提取-OCR字幕识别\tmp_imgs\如何给我们的PyQt6程序制作一个炫酷的充值按钮'):
    res_list=[]
    zimu_path=file_path+'-识别结果'
    zimu_files=os.listdir(zimu_path)
    zimu_files.sort(key=lambda x:int(x[14:20]))
    for file in zimu_files:
        zimu_file_path=os.path.join(zimu_path,file)
        result=extract_zimu_from_file(zimu_file_path)
        if result:
            res_list.append(result)
    res_list=list(dict.fromkeys(res_list))
    # res_list=handke_repeat_list(res_list)
    print('，'.join(res_list))

connect_center_result()