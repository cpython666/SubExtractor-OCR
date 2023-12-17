import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QLabel, QFileDialog, QListWidget, QHBoxLayout,
                             QLineEdit, QTextEdit,QProgressBar,
                             QMessageBox)
from PyQt6.QtGui import QIcon, QGuiApplication, QDesktopServices
from PyQt6.QtCore import QUrl, Qt,QThread,pyqtSignal
from qt_material import apply_stylesheet
import cv2
import numpy as np
import os
import json
from wechat_ocr.ocr_manager import OcrManager, OCR_MAX_TASK_ID
class WorkerThread(QThread):
    progress_zimu_signal = pyqtSignal(int,int)
    progress_ocr_signal = pyqtSignal(int,int)
    progress_connect_signal = pyqtSignal(int,int)
    finished_signal = pyqtSignal()
    message_signal = pyqtSignal(str)
    def set_video_path(self, path_videos,wxocr_path,wx_path):
        self.path_videos = path_videos
        self.wxocr_path = wxocr_path
        self.wx_path = wx_path
    def run(self):
        self.ocr_manager = OcrManager(self.wx_path)
        self.ocr_manager.SetExePath(self.wxocr_path)
        self.ocr_manager.SetUsrLibDir(self.wx_path)
        self.ocr_manager.SetOcrResultCallback(self.ocr_result_callback)
        self.ocr_manager.StartWeChatOCR()
        for path_video in self.path_videos:
            self.path_video=path_video
            self.name_video, file_extension = os.path.splitext(os.path.basename(self.path_video))
            self.message_signal.emit(f"开始识别{self.name_video}的字幕！")
            self.initFolder()
            self.get_video_zimu_imgs()
            self.message_signal.emit("字母区域裁剪完成，开始识别~")
            self.ocr_zimu()
            self.message_signal.emit("字幕识别完成~")
            self.connect_center_result()
            self.message_signal.emit(f"输出结果至-->{self.path_output}完成！")
            # self.deleteFolder()
            # self.message_signal.emit("删除中间文件完成！")
            self.message_signal.emit("请手动删除中间文件！")
            self.finished_signal.emit()

        self.ocr_manager.KillWeChatOCR()


    def initFolder(self):
        self.path_zimu = f'tmp_imgs/{self.name_video}-字幕'
        self.path_output_ocr = f'tmp_imgs/{self.name_video}-识别结果'
        self.path_output = 'output'
        if not os.path.exists(self.path_zimu):
            os.makedirs(self.path_zimu)
        if not os.path.exists(self.path_output_ocr):
            os.makedirs(self.path_output_ocr)
        if not os.path.exists(self.path_output):
            os.mkdir(self.path_output)
    def deleteFolder(self):
        self.delete_folder(self.path_zimu)
        self.delete_folder(self.path_output_ocr)
    def get_video_zimu_imgs(self):
        cap = cv2.VideoCapture(self.path_video)
        if not cap.isOpened():
            print("无法打开视频文件")
            self.output_info.append('无法打开视频文件')
        else:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # print(f"视频总帧数: {total_frames}")
            frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
            # print(f"视频帧率: {frame_rate} fps")
            self.message_signal.emit(f"视频总帧数: {total_frames}")
            self.message_signal.emit(f"视频帧率: {frame_rate} fps")
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
                    image_save_path = os.path.join(self.path_zimu, image_filename)
                    new_frame=self.cut_frame(frame)
                    cv2.imencode(".png", new_frame)[1].tofile(image_save_path)
                    self.progress_zimu_signal.emit(frame_count // frame_interval,total_frames // frame_interval)
                    # break
                    # TODO
                frame_count += 1

        cap.release()
    def extract_zimu_from_file(self, file):
        with open(file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        zimu_width = self.image_width
        print(file)
        if data:
            ocrResult = data['ocrResult']
            ocrResult=[i for i in ocrResult if i['location']['right'] and i['location']['left']]
            # ocrResult=[i for i in ocrResult if i['location']['right'] and i['location']['left'] and i['location']['top'] and i['location']['bottom']]
            if ocrResult:
                # 方案一：最宽字幕区间
                ocrResult.sort(key=lambda x: -1 * (x['location']['right'] - x['location']['left']))
                # 方案二：最高字幕区间
                # ocrResult.sort(key=lambda x: (x['location']['top'] - x['location']['bottom']))
                # 方案三：最大面积
                # ocrResult.sort(key=lambda x: -1 * (x['location']['right'] - x['location']['left'])*(x['location']['bottom'] - x['location']['top']))
                center = ocrResult[0]['location']['left'] + ocrResult[0]['location']['right']
                if abs(center - zimu_width) < 100:
                    print(ocrResult[0]['text'])
                    return ocrResult[0]['text']
        else:
            return False
    def cv_imread(self, file_path):
        cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), -1)
        return cv_img
    def cut_frame(self,frame):
        self.image_width = frame.shape[1]
        self.image_height = frame.shape[0]
        height_min=int(self.image_height*0.8)
        crop_area = (0, height_min, self.image_width, self.image_height-height_min)
        x, y, w, h = crop_area
        return frame[y:y + h, x:x + w]
    def ocr_result_callback(self, img_path: str, results: dict):
        zimu_imgs_path = os.path.dirname(img_path).replace('-字幕', '-识别结果')
        zimu_imgs_name = os.path.basename(img_path)
        result_file = os.path.join(zimu_imgs_path, zimu_imgs_name) + ".json"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(results, ensure_ascii=False, indent=2))
    def ocr_zimu(self):
        zimu_path = self.path_zimu
        output_path = self.path_output_ocr

        image_files = [f'{f}' for f in os.listdir(zimu_path)]
        total=len(image_files)
        for image_name in image_files:
            image_path = os.path.join(zimu_path, image_name)
            self.ocr_manager.DoOCRTask(image_path)
            self.progress_ocr_signal.emit(image_files.index(image_name)+1,total)
        while self.ocr_manager.m_task_id.qsize() != OCR_MAX_TASK_ID:
            pass
    def connect_center_result(self):
        res_list = []
        zimu_path = self.path_output_ocr
        zimu_files = os.listdir(zimu_path)
        zimu_files.sort(key=lambda x: int(x[6:12]))
        total=len(zimu_files)
        for file in zimu_files:
            zimu_file_path = os.path.join(zimu_path, file)
            result = self.extract_zimu_from_file(zimu_file_path)
            if result:
                res_list.append(result)
            self.progress_connect_signal.emit(zimu_files.index(file)+1,total)
        res_list = list(dict.fromkeys(res_list))
        print('，'.join(res_list))
        self.message_signal.emit('，'.join(res_list))
        with open(self.path_output+'/' + self.name_video + '.txt', 'w', encoding='utf-8') as f:
            f.write('，'.join(res_list))
    def delete_folder(self, folder_path):
        try:
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    os.rmdir(dir_path)
            os.rmdir(folder_path)
            print(f"文件夹 '{folder_path}' 已成功删除.")
        except Exception as e:
            print(f"删除文件夹 '{folder_path}' 时发生错误: {e}")

class VideoProcessingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.selected_files = []
        self.txt_output_path = os.path.join(os.path.dirname(__file__), "output")

        self.init_ui()
        self.center()
    def center(self):
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show_file_dialog(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle('选择一个文件')
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        # 显示文件选择框并等待用户选择
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            # 获取用户选择的文件路径
            selected_file = file_dialog.selectedFiles()[0]
            self.test_file_label.setText(f'当前已选择图片{selected_file}')
            self.test_file = selected_file

    def init_ui(self):
        self.setWindowIcon(QIcon('logo.png'))
        self.setGeometry(0, 0, 800, 600)
        layout = QVBoxLayout()
        if not os.path.exists('config.txt'):
            self.setWindowTitle('测试wx_OCR是否可用')
            self.test_results = None
            # 验证WX-OCR功能
            self.wxocr_path_label = QLabel(
                r'请输入wx的ocr的路径：【仿照寻找自己电脑中的路径】C:\Users\86159\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7061\extracted\WeChatOCR.exe')
            self.wxocr_path_label.setTextInteractionFlags(
                self.wxocr_path_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)
            self.wxocr_path_edit = QLineEdit()
            self.wxocr_path_edit.setText(
                r'C:\Users\86159\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7061\extracted\WeChatOCR.exe')
            self.wx_path_label = QLabel(r'请输入wx的ocr的路径：【仿照寻找自己电脑中的路径】D:\微信\WeChat\[3.9.8.15]')
            self.wx_path_label.setTextInteractionFlags(
                self.wx_path_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)
            self.wx_path_edit = QLineEdit()
            self.wx_path_edit.setText(r'D:\微信\WeChat\[3.9.8.15]')
            self.test_file_label = QLabel('当前未选择测试图片！')
            self.test_file_button = QPushButton('选择测试图片')
            self.test_file = None
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
            self.wxocr_path = data[0]
            self.wx_path = data[1]
            self.setWindowTitle('字幕提取器-2.0')
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
            self.output_dir_label = QLabel(f'最终字幕拼接结果输出至:{self.txt_output_path}' + '/{视频名称}.txt')
            options_layout.addWidget(self.output_dir_label)

            self.progress_bar_zimu = QProgressBar(self)
            layout.addWidget(QLabel('分离字幕图片进度：'))
            layout.addWidget(self.progress_bar_zimu)
            self.progress_bar_ocr = QProgressBar(self)
            layout.addWidget(QLabel('字幕图片识别进度：'))
            layout.addWidget(self.progress_bar_ocr)
            self.progress_bar_connect = QProgressBar(self)
            layout.addWidget(QLabel('识别结果拼接进度：'))
            layout.addWidget(self.progress_bar_connect)

            layout.addLayout(options_layout)
            self.output_info = QTextEdit()
            self.output_info.setReadOnly(True)
            layout.addWidget(self.output_info)
            start_btn1 = QPushButton('开始处理')
            start_btn1.clicked.connect(self.start_processing)
            layout.addWidget(start_btn1)

        auther_layout = self.get_link_layout()
        layout.addLayout(auther_layout)
        main_widget = QWidget()
        main_widget.setLayout(layout)

        self.setCentralWidget(main_widget)
    def start_processing(self):
        # 创建并启动工作线程
        self.worker_thread = WorkerThread(self)
        self.worker_thread.set_video_path(path_videos=self.selected_files,wxocr_path=self.wxocr_path,wx_path=self.wx_path)
        self.worker_thread.progress_zimu_signal.connect(self.update_progress_zimu)
        self.worker_thread.progress_ocr_signal.connect(self.update_progress_ocr)
        self.worker_thread.progress_connect_signal.connect(self.update_progress_connect)
        self.init_process_bar()
        self.worker_thread.message_signal.connect(self.update_output)
        self.worker_thread.finished_signal.connect(self.init_process_bar)
        self.worker_thread.start()
        if not self.selected_files:
            QMessageBox.information(self, '提示', '请先选择文件',
                                    QMessageBox.StandardButton.Ok)
    def update_output(self,info):
        self.output_info.append(info)
    def update_progress_zimu(self,now,total):
        self.progress_bar_zimu.setRange(0,total)
        self.progress_bar_zimu.setValue(now)
    def init_process_bar(self):
        self.progress_bar_zimu.setValue(0)
        self.progress_bar_ocr.setValue(0)
        self.progress_bar_connect.setValue(0)

    def update_progress_ocr(self,now,total):
        self.progress_bar_ocr.setRange(0,total)
        self.progress_bar_ocr.setValue(now)
    def update_progress_connect(self,now,total):
        self.progress_bar_connect.setRange(0,total)
        self.progress_bar_connect.setValue(now)
    def open_browser(self, link):
        url = QUrl(link)
        # 使用QDesktopServices打开默认浏览器
        QDesktopServices.openUrl(url)
    def get_link_layout(self, text="Made By", des='派森斗罗【使用教程也在此处】',
                        link='https://space.bilibili.com/1909782963'):
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
    def add_file(self):
        file, _ = QFileDialog.getOpenFileNames(self, '选择视频文件', '', '视频文件 (*.mp4 *.avi *.mkv);;所有文件 (*)')
        if file:
            self.selected_files.clear()
            self.selected_files.extend(file)
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
    def verify_scuess(self, img_path: str, results: dict):
        self.test_results = results
    def verify_wx(self, file_path):
        if self.wx_path_edit.text() == '' or self.wxocr_path_edit.text() == '' or file_path == None:
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
            with open('config.txt', 'w', encoding='utf-8') as f:
                f.write(f'{self.wxocr_path_edit.text()}\n{self.wx_path_edit.text()}')
            QMessageBox.information(self, '提示',
                                    f'识别结果是{self.test_results}，\nwx_ocr验证成功，\n已将配置保存在config.txt文件中，\n下次使用软件无需配置。\n点击确认关闭软件，\n之后再次打开软件即可开始使用',
                                    QMessageBox.StandardButton.Ok)
            self.close()

        else:
            QMessageBox.information(self, '提示', f'测试失败，请检查路径，如果实在找不到原因可以联系UP',
                                    QMessageBox.StandardButton.Ok)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_blue.xml')
    window = VideoProcessingApp()
    window.show()
    sys.exit(app.exec())
