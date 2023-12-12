import os
import json
import time
from wechat_ocr.ocr_manager import OcrManager, OCR_MAX_TASK_ID

wechat_ocr_dir = r"C:\Users\86159\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7061\extracted\WeChatOCR.exe"
# wechat_ocr_dir = "C:\\Users\\Administrator\\AppData\\Roaming\\Tencent\\WeChat\\XPlugin\\Plugins\\WeChatOCR\\7057\\extracted\\WeChatOCR.exe"
wechat_dir = r"D:\微信\WeChat\[3.9.8.15]"
# wechat_dir = "D:\\GreenSoftware\\WeChat\\3.9.6.32"

def ocr_result_callback(img_path: str, results: dict):
    zimu_imgs_path=os.path.dirname(img_path).replace('-字幕','-识别结果')
    zimu_imgs_name=os.path.basename(img_path)
    result_file = os.path.join(zimu_imgs_path,zimu_imgs_name)+".json"
    # result_file = os.path.basename(img_path) + ".json"
    print(f"识别成功，img_path: {img_path}, result_file: {result_file}")
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(results, ensure_ascii=False, indent=2))

def ocr_zimu(file_name=r'D:\文件夹\github_\myshare_github\Python-Project-Pro\视频文案提取-OCR字幕识别\tmp_imgs\如何给我们的PyQt6程序制作一个炫酷的充值按钮'):
    zimu_path=file_name+'-字幕'
    output_path=file_name+'-识别结果'
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    ocr_manager = OcrManager(wechat_dir)
    # 设置WeChatOcr目录
    ocr_manager.SetExePath(wechat_ocr_dir)
    # 设置微信所在路径
    ocr_manager.SetUsrLibDir(wechat_dir)
    # 设置ocr识别结果的回调函数
    ocr_manager.SetOcrResultCallback(ocr_result_callback)
    # 启动ocr服务
    ocr_manager.StartWeChatOCR()
    # 开始识别图片
    image_files = [f'{f}' for f in os.listdir(zimu_path)]
    for image_name in image_files:
        image_path=os.path.join(zimu_path,image_name)
        ocr_manager.DoOCRTask(image_path)
    # time.sleep(1)
    while ocr_manager.m_task_id.qsize() != OCR_MAX_TASK_ID:
        pass
    # 识别输出结果
    ocr_manager.KillWeChatOCR()


if __name__ == "__main__":
    ocr_zimu()
