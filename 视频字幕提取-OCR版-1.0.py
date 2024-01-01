import sys
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,
                             QPushButton, QLabel, QFileDialog, QListWidget, QHBoxLayout,
                             QLineEdit,QTextEdit, QCheckBox,
                             QMessageBox,QSpinBox)
from PyQt6.QtGui import QIcon,QGuiApplication,QDesktopServices
from PyQt6.QtCore import QUrl,Qt
from qt_material import apply_stylesheet
import cv2
import numpy as np
import os
import json
from wechat_ocr.ocr_manager import OcrManager, OCR_MAX_TASK_ID

class VideoProcessingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_files = []
        self.txt_output_path=os.path.join(os.path.dirname(__file__),"output")
        
        self.init_ui()
        self.center()

    def first_init_folders(self,file_name):
        self.path_frames=f'tmp_imgs/{file_name}'
        self.path_zimu=f'tmp_imgs/{file_name}-字幕'
        self.path_output_=f'tmp_imgs/{file_name}-识别结果'
        self.path_output='output/'
        if not os.path.exists('output'):
            os.mkdir('output')
        if not os.path.exists(f'tmp_imgs/{file_name}'):
            os.makedirs(f'tmp_imgs/{file_name}')
        if not os.path.exists(f'tmp_imgs/{file_name}-字幕'):
            os.makedirs(f'tmp_imgs/{file_name}-字幕')
        if not os.path.exists(f'tmp_imgs/{file_name}-识别结果'):
            os.makedirs(f'tmp_imgs/{file_name}-识别结果')

    def center(self):
        qr=self.frameGeometry()
        cp=QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def changeTheme(self):
        action=self.sender()
        theme_name=action.text()
        apply_stylesheet(app, theme=theme_name)

    def show_file_dialog(self):
        # 创建文件选择框
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle('选择一个文件')
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        # 显示文件选择框并等待用户选择
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            # 获取用户选择的文件路径
            selected_file = file_dialog.selectedFiles()[0]
            self.test_file_label.setText(f'当前已选择图片{selected_file}')
            self.test_file=selected_file

    def init_ui(self):
        self.setWindowIcon(QIcon('logo.png'))
        self.setGeometry(0, 0, 800, 600)
        layout = QVBoxLayout()
        if not os.path.exists('config.txt'):
            self.setWindowTitle('测试wx_OCR是否可用')
            self.test_results=None
            # 验证WX-OCR功能
            self.wxocr_path_label = QLabel(
                r'请输入wx的ocr的路径：【仿照寻找自己电脑中的路径】C:\Users\86159\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7061\extracted\WeChatOCR.exe')
            self.wxocr_path_label.setTextInteractionFlags(self.wxocr_path_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)
            self.wxocr_path_edit = QLineEdit()
            self.wxocr_path_edit.setText(r'C:\Users\86159\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7061\extracted\WeChatOCR.exe')
            self.wx_path_label = QLabel(r'请输入wx的ocr的路径：【仿照寻找自己电脑中的路径】D:\微信\WeChat\[3.9.8.15]')
            self.wx_path_label.setTextInteractionFlags(self.wx_path_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)
            self.wx_path_edit = QLineEdit()
            self.wx_path_edit.setText(r'D:\微信\WeChat\[3.9.8.15]')
            self.test_file_label = QLabel('当前未选择测试图片！')
            self.test_file_button = QPushButton('选择测试图片')
            self.test_file=None
            self.test_file_button.clicked.connect(self.show_file_dialog)
            self.wx_button = QPushButton('验证wx-OCR是否可用')
            self.wx_button.clicked.connect(lambda x: self.verify_wx(self.test_file))
            layout.addWidget(self.wxocr_path_label)
            layout.addWidget(self.wxocr_path_edit)
            layout.addWidget(self.wx_path_label)
            layout.addWidget(self.wx_path_edit)
            layout.addWidget(self.test_file_label)
            layout.addWidget(self.test_file_button)
            layout.addWidget(self.wx_button)
        else:
            with open('config.txt', 'r', encoding='utf-8') as f:
                data = f.read().split('\n')
            self.wxocr_path=data[0]
            self.wx_path=data[1]
            self.setWindowTitle('字幕提取器')
            # 文件选择
            file_layout = QHBoxLayout()
            self.file_label = QLabel('已选择文件:')
            file_layout.addWidget(self.file_label)
            self.file_list = QListWidget()
            file_layout.addWidget(self.file_list)
            file_btn_layout = QVBoxLayout()
            add_file_btn = QPushButton('添加文件')
            add_file_btn.clicked.connect(self.add_file)
            file_btn_layout.addWidget(add_file_btn)
            remove_file_btn = QPushButton('移除选中文件')
            remove_file_btn.clicked.connect(self.remove_selected_file)
            file_btn_layout.addWidget(remove_file_btn)
            file_layout.addLayout(file_btn_layout)
            layout.addLayout(file_layout)
            # 选项设置
            options_layout = QVBoxLayout()
            self.delete_temp_frames_checkbox = QCheckBox('字幕提取成功后删除临时抽帧图片')
            self.delete_temp_frames_checkbox.setChecked(True)
            options_layout.addWidget(self.delete_temp_frames_checkbox)
            self.delete_subtitles_checkbox = QCheckBox('字幕提取成功后删除字幕图片')
            self.delete_subtitles_checkbox.setChecked(True)
            options_layout.addWidget(self.delete_subtitles_checkbox)
            self.delete_json_checkbox = QCheckBox('字幕提取成功后删除识别中间文件')
            self.delete_json_checkbox.setChecked(True)
            options_layout.addWidget(self.delete_json_checkbox)
            self.output_dir_label1 = QLabel('视频抽帧图片将会被保存至:./tmp-imgs/{视频名称}')
            options_layout.addWidget(self.output_dir_label1)
            self.output_dir_label2 = QLabel('字幕图片将会被保存至:./tmp-imgs/{视频名称}-字幕')
            options_layout.addWidget(self.output_dir_label2)
            self.output_dir_label3 = QLabel('识别中间结果将会被保存至:./tmp-imgs/{视频名称}-识别结果')
            options_layout.addWidget(self.output_dir_label3)
            self.output_dir_label = QLabel(f'最终字幕拼接结果输出至:{self.txt_output_path}'+'/{视频名称}.txt')
            options_layout.addWidget(self.output_dir_label)

            layout.addLayout(options_layout)
            # 进度条和输出信息
            self.output_info = QTextEdit()
            self.output_info.setReadOnly(True)
            layout.addWidget(self.output_info)
            # 开始处理按钮
            start_label=QLabel('先将所有视频进行抽帧处理,测量出各自视频字幕高度区间，填入后再进行第二个按钮操作')
            layout.addWidget(start_label)
            start_btn1 = QPushButton('视频抽帧')
            start_btn1.clicked.connect(self.start_processing_1)
            layout.addWidget(start_btn1)
            height_layout=QHBoxLayout()
            height_layout.addWidget(QLabel('请输入高度区间：'))
            self.height_min=QSpinBox()
            self.height_min.setMinimum(0)  # 设置最小值
            self.height_min.setMaximum(8000)  # 设置最大值
            self.height_min.setValue(1800)  # 设置初始值
            height_layout.addWidget(self.height_min)
            self.height_max=QSpinBox()
            self.height_max.setMinimum(0)  # 设置最小值
            self.height_max.setMaximum(8000)  # 设置最大值
            self.height_max.setValue(1950)  # 设置初始值
            height_layout.addWidget(self.height_max)
            layout.addLayout(height_layout)
            start_btn2 = QPushButton('裁剪字幕->识别字幕->连接结果')
            start_btn2.clicked.connect(self.start_processing_2)
            layout.addWidget(start_btn2)

        auther_layout=self.get_link_layout()
        layout.addLayout(auther_layout)
        main_widget=QWidget()
        main_widget.setLayout(layout)

        self.setCentralWidget(main_widget)

    def open_browser(self, link):
        url = QUrl(link)
        # 使用QDesktopServices打开默认浏览器
        QDesktopServices.openUrl(url)

    def get_link_layout(self, text="Made By", des='派森斗罗【使用教程也在此处】', link='https://space.bilibili.com/1909782963'):
        layout = QHBoxLayout()
        label = QLabel(text)
        open_button = QPushButton(des, self)
        font = open_button.font()
        font.setUnderline(True)
        open_button.setFont(font)
        open_button.setStyleSheet("border:0;")
        open_button.clicked.connect(lambda: self.open_browser(link))
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addWidget(open_button)
        layout.addStretch(1)
        return layout

    def start_processing_1(self):
        if self.selected_files:
            file_path=self.selected_files[0]
            file_name, file_extension = os.path.splitext(os.path.basename(file_path))
            self.first_init_folders(file_name)
            self.get_video_frames(video_path=file_path,folder_path=self.path_frames)
        else:
            QMessageBox.information(self, '提示', '选择文件后才能进行视频抽帧操作',
                                    QMessageBox.StandardButton.Ok)

    def add_file(self):
        file, _ = QFileDialog.getOpenFileName(self, '选择视频文件', '', '视频文件 (*.mp4 *.avi *.mkv);;所有文件 (*)')
        if file:
            self.selected_files.clear()
            self.selected_files.append(file)
            self.update_file_list()

    def update_file_list(self):
        self.file_list.clear()
        for file in self.selected_files:
            self.file_list.addItem(file)

    def remove_selected_file(self):
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            self.selected_files.remove(item.text())
        self.update_file_list()

    def get_video_frames(self,video_path,
                     folder_path):
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        # 检查视频是否成功打开
        if not cap.isOpened():
            print("无法打开视频文件")
            self.output_info.append('无法打开视频文件')
        else:
            # 获取视频帧数
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # print(f"视频总帧数: {total_frames}")
            frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
            # print(f"视频帧率: {frame_rate} fps")
            self.output_info.append(f"视频总帧数: {total_frames}")
            self.output_info.append(f"视频帧率: {frame_rate} fps")
            QApplication.processEvents()
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
                    cv2.imencode(".png",frame)[1].tofile(image_save_path)
                    # print(f"保存图像:{image_filename},视频抽帧进度:{frame_count//frame_interval}/{total_frames//frame_interval}:{frame_count}/{total_frames}")
                    self.output_info.append(f"保存图像:{image_filename},视频抽帧进度:{frame_count//frame_interval}/{total_frames//frame_interval}:{frame_count}/{total_frames}")
                    QApplication.processEvents()

                frame_count += 1
        cap.release()

    def cv_imread(self,file_path):
        cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), -1)
        return cv_img

    def start_processing_2(self):
        file_path=self.selected_files[0]
        if self.selected_files:
            file_name, file_extension = os.path.splitext(os.path.basename(file_path))
            self.first_init_folders(file_name)
            self.cut_zimu_from_img(imgs_path=self.path_frames)
            self.ocr_zimu(file_name=self.path_frames)
            self.connect_center_result(file_path=self.path_frames,file_name=file_name)
            # 删除文件夹
            if self.delete_temp_frames_checkbox.isChecked():
                self.delete_folder(self.path_frames)
            if self.delete_subtitles_checkbox.isChecked():
                self.delete_folder(self.path_zimu)
            if self.delete_json_checkbox.isChecked():
                self.delete_folder(self.path_output_)

    def delete_folder(self,folder_path):
        try:
            # 列出文件夹中的所有文件和子文件夹
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 删除文件
                    os.remove(file_path)
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    # 删除子文件夹
                    os.rmdir(dir_path)
            # 删除最顶层的文件夹
            os.rmdir(folder_path)
            print(f"文件夹 '{folder_path}' 已成功删除.")
            self.output_info.append(f"文件夹 '{folder_path}' 已成功删除.")
            QApplication.processEvents()
        except Exception as e:
            print(f"删除文件夹 '{folder_path}' 时发生错误: {e}")
            self.output_info.append(f"删除文件夹 '{folder_path}' 时发生错误: {e}")
            QApplication.processEvents()

    def cut_zimu_from_img(self,
            imgs_path):
        zimu_folder_name = os.path.basename(imgs_path) + '-字幕'
        zimu_path = os.path.join(os.path.dirname(imgs_path), zimu_folder_name)
        # 获取文件夹中的所有图片文件
        image_files = [f for f in os.listdir(imgs_path)]
        # 定义裁剪区域的坐标 (x, y, width, height)
        image_path = os.path.join(imgs_path, image_files[0])
        image = self.cv_imread(image_path)
        height_min = int(self.height_min.text())
        height_max = int(self.height_max.text())
        self.image_width = image.shape[1]
        crop_area = (0, height_min, self.image_width, height_max - height_min)
        # 循环处理每个图片文件
        for image_file in image_files:
            # 拼接图片文件的完整路径
            image_path = os.path.join(imgs_path, image_file)
            # 读取图片
            image = self.cv_imread(image_path)
            if image is not None:
                # 裁剪图片
                x, y, w, h = crop_area
                cropped_image = image[y:y + h, x:x + w]
                # 保存裁剪后的图片
                output_file = os.path.normpath(os.path.join(zimu_path, f"cropped_{image_file}"))
                cv2.imencode(".png", cropped_image)[1].tofile(output_file)

                print(f"已保存裁剪后的图片：{output_file}")
                self.output_info.append(f"已保存裁剪后的图片：{output_file}")
                QApplication.processEvents()
            else:
                print(f"无法读取图片：{image_path}")
                self.output_info.append(f"无法读取图片：{image_path}")
                QApplication.processEvents()

    def ocr_result_callback(self,img_path: str, results: dict):
        zimu_imgs_path = os.path.dirname(img_path).replace('-字幕', '-识别结果')
        zimu_imgs_name = os.path.basename(img_path)
        result_file = os.path.join(zimu_imgs_path, zimu_imgs_name) + ".json"
        # print(f"识别成功，img_path: {img_path}, result_file: {result_file}")
        self.output_info.append(f"识别成功，img_path: {img_path}, result_file: {result_file}")
        QApplication.processEvents()
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(results, ensure_ascii=False, indent=2))

    def ocr_zimu(self,file_name):
        zimu_path = file_name + '-字幕'
        output_path = file_name + '-识别结果'
        ocr_manager = OcrManager(self.wx_path)
        # 设置WeChatOcr目录
        ocr_manager.SetExePath(self.wxocr_path)
        # 设置微信所在路径
        ocr_manager.SetUsrLibDir(self.wx_path)
        # 设置ocr识别结果的回调函数
        ocr_manager.SetOcrResultCallback(self.ocr_result_callback)
        # 启动ocr服务
        ocr_manager.StartWeChatOCR()
        # 开始识别图片
        image_files = [f'{f}' for f in os.listdir(zimu_path)]
        for image_name in image_files:
            image_path = os.path.join(zimu_path, image_name)
            ocr_manager.DoOCRTask(image_path)
            self.output_info.append(f"正在识别{image_path}中。。。")
            QApplication.processEvents()
        # time.sleep(1)
        # counter=0
        while ocr_manager.m_task_id.qsize() != OCR_MAX_TASK_ID:
            # time.sleep(0.5)
            # counter+=1
            # if counter>=6:
            #     break
            pass
        # 识别输出结果
        ocr_manager.KillWeChatOCR()
    def verify_scuess(self,img_path: str, results: dict):
        self.test_results=results

    def verify_wx(self,file_path):
        if self.wx_path_edit.text()=='' or self.wxocr_path_edit.text()=='' or file_path ==None:
            QMessageBox.information(self, '提示', 'wxocr_path，wx_path和测试图片路径三者都不能为空',
                                    QMessageBox.StandardButton.Ok)
            return
        print(self.wx_path_edit.text())
        print(self.wxocr_path_edit.text())
        ocr_manager = OcrManager(self.wx_path_edit.text())
        # 设置WeChatOcr目录
        ocr_manager.SetExePath(self.wxocr_path_edit.text())
        # 设置微信所在路径
        ocr_manager.SetUsrLibDir(self.wx_path_edit.text())
        # 设置ocr识别结果的回调函数
        ocr_manager.SetOcrResultCallback(self.verify_scuess)
        # 启动ocr服务
        ocr_manager.StartWeChatOCR()
        # 开始识别图片
        ocr_manager.DoOCRTask(file_path)
        # time.sleep(1)
        while ocr_manager.m_task_id.qsize() != OCR_MAX_TASK_ID:
            pass
        # 识别输出结果
        ocr_manager.KillWeChatOCR()
        if self.test_results:
            with open('config.txt','w',encoding='utf-8') as f:
                f.write(f'{self.wxocr_path_edit.text()}\n{self.wx_path_edit.text()}')
            QMessageBox.information(self, '提示', f'识别结果是{self.test_results}，\nwx_ocr验证成功，\n已将配置保存在config.txt文件中，\n下次使用软件无需配置。\n点击确认关闭软件，\n之后再次打开软件即可开始使用',
                                    QMessageBox.StandardButton.Ok)
            self.close()

        else:
            QMessageBox.information(self, '提示', f'测试失败，请检查路径，如果实在找不到原因可以联系UP',
                                    QMessageBox.StandardButton.Ok)

    def extract_zimu_from_file(self,file):
        with open(file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        zimu_width = self.image_width
        if data:
            # print(data)
            ocrResult = data['ocrResult']
            if ocrResult:
                ocrResult.sort(key=lambda x: -1 * (x['location']['right'] - x['location']['left']))
                res = ''
                for ocrresult in ocrResult[:3]:
                    center = ocrresult['location']['left'] + ocrresult['location']['right']
                    if abs(center - zimu_width) < 100:
                        print(ocrresult['text'])
                        res+=ocrresult['text']
                return res
        else:
            return False

    def connect_center_result(self,
            file_path,file_name):
        res_list = []
        zimu_path = file_path + '-识别结果'
        zimu_files = os.listdir(zimu_path)
        zimu_files.sort(key=lambda x: int(x[14:20]))
        for file in zimu_files:
            zimu_file_path = os.path.join(zimu_path, file)
            result = self.extract_zimu_from_file(zimu_file_path)
            if result:
                res_list.append(result)
        res_list = list(dict.fromkeys(res_list))
        print('，'.join(res_list))
        self.output_info.append('，'.join(res_list))
        QApplication.processEvents()
        with open(self.path_output+file_name+'.txt','w',encoding='utf-8') as f:
            f.write('，'.join(res_list))

if __name__ == '__main__':

    # wechat_ocr_dir = r"C:\Users\86159\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7061\extracted\WeChatOCR.exe"
    # wechat_ocr_dir = "C:\\Users\\Administrator\\AppData\\Roaming\\Tencent\\WeChat\\XPlugin\\Plugins\\WeChatOCR\\7057\\extracted\\WeChatOCR.exe"
    # wechat_dir = r"D:\微信\WeChat\[3.9.8.15]"
    # wechat_dir = "D:\\GreenSoftware\\WeChat\\3.9.6.32"
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_blue.xml')
    window = VideoProcessingApp()
    window.show()
    sys.exit(app.exec())
