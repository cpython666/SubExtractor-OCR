import sys
import os
import json
import base64
import requests
import cv2
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QPushButton, QLabel, QFileDialog, QListWidget, QHBoxLayout,
                               QLineEdit, QTextEdit, QProgressBar, QMessageBox)
from PySide6.QtGui import QIcon, QGuiApplication, QDesktopServices
from PySide6.QtCore import QUrl, Qt, QThread, Signal
from qt_material import apply_stylesheet
from dotenv import load_dotenv

load_dotenv()
UMI_OCR_URL = os.getenv("UMI_OCR_URL", 'http://127.0.0.1:1224/api/ocr')


class SubtitleExtractor(QThread):
    """字幕提取的工作线程，负责处理视频并生成SRT和TXT字幕文件"""
    progress_extract_signal = Signal(int, int)  # 抽取字幕图片进度信号
    progress_ocr_signal = Signal(int, int)      # OCR识别进度信号
    progress_combine_signal = Signal(int, int)  # 字幕合并进度信号
    finished_signal = Signal()                  # 任务完成信号
    message_signal = Signal(str)                # 输出消息信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frames_per_second = 1  # 默认每秒抽取1帧，可通过UI配置

    def set_video_paths(self, video_paths, frames_per_second=1):
        """设置视频路径和每秒抽取帧数"""
        self.video_paths = video_paths
        self.frames_per_second = frames_per_second

    def run(self):
        """线程运行主函数，依次处理每个视频"""
        for video_path in self.video_paths:
            self.video_path = video_path
            self.video_name = os.path.splitext(os.path.basename(video_path))[0]
            self.message_signal.emit(f"开始提取{self.video_name}的字幕！")
            self.setup_directories()
            self.extract_subtitle_frames()
            self.message_signal.emit("字幕区域裁剪完成，开始OCR识别~")
            self.perform_ocr()
            self.message_signal.emit("字幕识别完成，开始合并~")
            self.generate_srt_and_txt_files()
            self.message_signal.emit(f"字幕已输出至: {self.output_dir}/{self.video_name}.srt 和 {self.output_dir}/{self.video_name}.txt")
            self.message_signal.emit("请手动删除临时文件！")
        self.finished_signal.emit()

    def setup_directories(self):
        """初始化临时目录和输出目录"""
        self.subtitle_dir = f'tmp_imgs/{self.video_name}-字幕'
        self.ocr_result_dir = f'tmp_imgs/{self.video_name}-识别结果'
        self.output_dir = 'output'
        os.makedirs(self.subtitle_dir, exist_ok=True)
        os.makedirs(self.ocr_result_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_subtitle_frames(self):
        """从视频中抽取字幕区域的帧并保存为图片"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.message_signal.emit('无法打开视频文件')
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
        duration = total_frames / frame_rate if frame_rate > 0 else 0
        self.message_signal.emit(f"视频总帧数: {total_frames}")
        self.message_signal.emit(f"视频帧率: {frame_rate} fps")
        self.message_signal.emit(f"视频时长: {duration:.2f} 秒")

        # 获取视频宽高
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.message_signal.emit(f"视频宽高: {width}x{height}")

        # 计算抽帧间隔
        frame_interval = frame_rate // self.frames_per_second
        frame_count = 0
        extracted_count = 0
        total_extracted = total_frames // frame_interval

        # 计算帧号的填充位数
        padding_length = math.ceil(math.log10(total_frames)) if total_frames > 0 else 6

        # 读取一帧以确定截取高度
        ret, frame = cap.read()
        if ret:
            crop_height_min = int(frame.shape[0] * 0.8)
            self.message_signal.emit(f"截取字幕高度区间: {crop_height_min} - {frame.shape[0]}")
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置到第一帧

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_interval == 0:
                image_filename = f"frame_{frame_count:0{padding_length}d}.png"
                image_path = os.path.join(self.subtitle_dir, image_filename)
                cropped_frame = self.crop_subtitle_area(frame)
                cv2.imencode(".png", cropped_frame)[1].tofile(image_path)
                extracted_count += 1
                self.progress_extract_signal.emit(extracted_count, total_extracted)
            frame_count += 1
        cap.release()

    def crop_subtitle_area(self, frame):
        """裁剪视频帧中的字幕区域（默认裁剪底部20%区域）"""
        height = frame.shape[0]
        height_min = int(height * 0.8)  # 字幕通常在底部
        return frame[height_min:, :]

    def perform_ocr(self):
        """对字幕图片进行OCR识别并保存结果"""
        image_files = [f for f in os.listdir(self.subtitle_dir) if f.endswith('.png')]
        total = len(image_files)
        api_url = UMI_OCR_URL

        for idx, image_name in enumerate(image_files):
            image_path = os.path.join(self.subtitle_dir, image_name)
            with open(image_path, 'rb') as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            data = {
                "base64": img_base64,
                "options": {"data.format": "dict"}
                # "options": {"data.format": "text"}
            }
            headers = {"Content-Type": "application/json"}

            data_str = json.dumps(data)
            retries = 3
            for attempt in range(retries):
                try:
                    response = requests.post(api_url, data=data_str,headers=headers, timeout=10)
                    if response.status_code == 200:
                        result = response.json()
                        print("result",result)
                        text = self.parse_ocr_result(result)
                        print("text",text)
                        result_file = os.path.join(self.ocr_result_dir, f"{image_name}.json")
                        with open(result_file, 'w', encoding='utf-8') as f:
                            json.dump({'text': text}, f, ensure_ascii=False, indent=2)
                        break
                    elif response.status_code == 502:
                        if attempt < retries - 1:
                            self.message_signal.emit(f"API返回502，正在重试... (尝试 {attempt + 1}/{retries})")
                        else:
                            self.message_signal.emit(f"API调用失败: 502，重试 {retries} 次后仍失败")
                    else:
                        self.message_signal.emit(f"OCR API调用失败: {response.status_code}")
                        break
                except Exception as e:
                    if attempt < retries - 1:
                        self.message_signal.emit(f"OCR处理出错: {str(e)}，正在重试... (尝试 {attempt + 1}/{retries})")
                    else:
                        self.message_signal.emit(f"OCR处理出错: {str(e)}，重试 {retries} 次后仍失败")
            self.progress_ocr_signal.emit(idx + 1, total)

    def parse_ocr_result(self, result):
        """解析UMI-OCR的返回结果，提取面积最大的一句话"""
        # 检查识别是否成功，code 为 100 表示成功
        if result.get('code') != 100:
            return ''

        # 获取 data 列表，若为空则返回空字符串
        data = result.get('data', [])
        if not data:
            return ''

        # 初始化最大面积和对应的文本
        max_area = 0
        max_text = ''

        # 遍历 data 中的每个文本项
        for item in data:
            box = item.get('box', [])
            # 确保 box 包含 4 个点（矩形）
            if len(box) != 4:
                continue

            # 计算矩形面积
            # box 格式为 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            # 宽 = x2 - x1，高 = y3 - y1
            width = box[1][0] - box[0][0]
            height = box[2][1] - box[0][1]
            area = width * height

            # 更新最大面积及其对应的文本
            if area > max_area:
                max_area = area
                max_text = item.get('text', '')

        return max_text

    def normalize_text(self, text):
        """归一化相近字符，例如将'—'替换为'-'"""
        normalization_map = {'—': '-'}
        for src, dst in normalization_map.items():
            text = text.replace(src, dst)
        return text

    def generate_srt_and_txt_files(self):
        """合并OCR结果并生成带时间线的SRT文件和TXT文件"""
        ocr_files = [f for f in os.listdir(self.ocr_result_dir) if f.endswith('.json')]
        ocr_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
        total = len(ocr_files)

        subtitles = []
        current_text = None
        start_frame = None
        frame_rate = int(cv2.VideoCapture(self.video_path).get(cv2.CAP_PROP_FPS))

        for idx, file in enumerate(ocr_files):
            file_path = os.path.join(self.ocr_result_dir, file)
            text = self.parse_ocr_json(file_path)
            if text:
                normalized_text = self.normalize_text(text)
                frame_num = int(file.split('_')[1].split('.')[0])
                if current_text is None:
                    current_text = normalized_text
                    start_frame = frame_num
                elif normalized_text != current_text:
                    end_frame = frame_num - 1
                    subtitles.append({
                        'start': start_frame / frame_rate,
                        'end': end_frame / frame_rate,
                        'text': current_text
                    })
                    current_text = normalized_text
                    start_frame = frame_num
            self.progress_combine_signal.emit(idx + 1, total)

        # 添加最后一个字幕
        if current_text is not None:
            end_frame = int(ocr_files[-1].split('_')[1].split('.')[0])
            subtitles.append({
                'start': start_frame / frame_rate,
                'end': end_frame / frame_rate,
                'text': current_text
            })

        # 生成SRT和TXT内容
        srt_content = ""
        txt_content = ""
        for i, sub in enumerate(subtitles, start=1):
            start_time = self.format_srt_time(sub['start'])
            end_time = self.format_srt_time(sub['end'])
            srt_content += f"{i}\n{start_time} --> {end_time}\n{sub['text']}\n\n"
            txt_content += f"{sub['text']}\n"

        # 写入SRT文件
        srt_path = os.path.join(self.output_dir, f"{self.video_name}.srt")
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        self.message_signal.emit("SRT文件生成完成！")

        # 写入TXT文件
        txt_path = os.path.join(self.output_dir, f"{self.video_name}.txt")

        res_list = list(dict.fromkeys(txt_content.split('\n')))
        print('，'.join(res_list))
        txt_content='，'.join(res_list)
        self.message_signal.emit('，'.join(res_list))
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_content)
        self.message_signal.emit("TXT文件生成完成！")

    def parse_ocr_json(self, file_path):
        """从JSON文件中提取OCR识别的文本"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('text', '')

    def format_srt_time(self, seconds):
        """将秒数转换为SRT时间格式（例如：00:00:01,000）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


class SubtitleApp(QMainWindow):
    """主窗口，提供用户界面交互"""
    def __init__(self):
        super().__init__()
        self.selected_videos = []
        self.output_dir = os.path.join(os.path.dirname(__file__), "output")
        self.init_ui()
        self.center_window()

    def center_window(self):
        """将窗口居中显示"""
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowIcon(QIcon('logo.png'))
        self.setGeometry(0, 0, 800, 600)
        self.setWindowTitle('字幕提取器')
        layout = QVBoxLayout()

        # 文件选择区域
        file_layout = QHBoxLayout()
        self.file_label = QLabel('已选择文件:')
        file_layout.addWidget(self.file_label)
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)
        file_btn_layout = QVBoxLayout()
        add_file_btn = QPushButton('添加文件')
        add_file_btn.clicked.connect(self.add_files)
        file_btn_layout.addWidget(add_file_btn)
        remove_file_btn = QPushButton('移除选中文件')
        remove_file_btn.clicked.connect(self.remove_selected_files)
        file_btn_layout.addWidget(remove_file_btn)
        file_layout.addLayout(file_btn_layout)
        layout.addLayout(file_layout)

        # 配置选项
        self.output_label = QLabel(f'字幕输出路径: {self.output_dir}/{{视频名称}}.srt 和 {{视频名称}}.txt')
        layout.addWidget(self.output_label)
        layout.addWidget(QLabel('每秒抽取帧数:'))
        self.fps_input = QLineEdit("1")
        layout.addWidget(self.fps_input)

        # 进度条
        self.progress_extract = QProgressBar(self)
        layout.addWidget(QLabel('字幕图片提取进度：'))
        layout.addWidget(self.progress_extract)
        self.progress_ocr = QProgressBar(self)
        layout.addWidget(QLabel('字幕OCR识别进度：'))
        layout.addWidget(self.progress_ocr)
        self.progress_combine = QProgressBar(self)
        layout.addWidget(QLabel('字幕合并进度：'))
        layout.addWidget(self.progress_combine)

        # 输出信息
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        # 开始按钮
        start_btn = QPushButton('开始处理')
        start_btn.clicked.connect(self.start_processing)
        layout.addWidget(start_btn)

        # 作者信息
        layout.addLayout(self.create_author_link())

        # 设置主窗口布局
        main_widget = QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def start_processing(self):
        """启动字幕提取进程"""
        if not self.selected_videos:
            QMessageBox.information(self, '提示', '请先选择视频文件', QMessageBox.StandardButton.Ok)
            return
        try:
            fps = int(self.fps_input.text())
            if fps <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.information(self, '提示', '每秒抽取帧数必须是正整数', QMessageBox.StandardButton.Ok)
            return

        self.extractor = SubtitleExtractor(self)
        self.extractor.set_video_paths(self.selected_videos, fps)
        self.extractor.progress_extract_signal.connect(self.update_extract_progress)
        self.extractor.progress_ocr_signal.connect(self.update_ocr_progress)
        self.extractor.progress_combine_signal.connect(self.update_combine_progress)
        self.extractor.message_signal.connect(self.update_output)
        self.extractor.finished_signal.connect(self.reset_progress)
        self.reset_progress()
        self.extractor.start()

    def update_output(self, message):
        """更新输出信息"""
        self.output_text.append(message)

    def update_extract_progress(self, current, total):
        """更新字幕提取进度"""
        self.progress_extract.setRange(0, total)
        self.progress_extract.setValue(current)

    def update_ocr_progress(self, current, total):
        """更新OCR识别进度"""
        self.progress_ocr.setRange(0, total)
        self.progress_ocr.setValue(current)

    def update_combine_progress(self, current, total):
        """更新字幕合并进度"""
        self.progress_combine.setRange(0, total)
        self.progress_combine.setValue(current)

    def reset_progress(self):
        """重置进度条"""
        self.progress_extract.setValue(0)
        self.progress_ocr.setValue(0)
        self.progress_combine.setValue(0)

    def add_files(self):
        """添加视频文件"""
        files, _ = QFileDialog.getOpenFileNames(self, '选择视频文件', '', '视频文件 (*.mp4 *.avi *.mkv);;所有文件 (*)')
        if files:
            self.selected_videos.clear()
            self.selected_videos.extend(files)
            self.update_file_list()

    def update_file_list(self):
        """更新文件列表显示"""
        self.file_list.clear()
        for file in self.selected_videos:
            self.file_list.addItem(file)

    def remove_selected_files(self):
        """移除选中的文件"""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            self.selected_videos.remove(item.text())
        self.update_file_list()

    def open_url(self, url):
        """在浏览器中打开链接"""
        QDesktopServices.openUrl(QUrl(url))

    def create_author_link(self, text="Made By", desc='派森斗罗【使用教程也在此处】',
                           url='https://space.bilibili.com/1909782963'):
        """创建作者信息和链接"""
        layout = QHBoxLayout()
        label = QLabel(text)
        link_btn = QPushButton(desc, self)
        font = link_btn.font()
        font.setUnderline(True)
        link_btn.setFont(font)
        link_btn.setStyleSheet("border:0;")
        link_btn.clicked.connect(lambda: self.open_url(url))
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addWidget(link_btn)
        layout.addStretch(1)
        return layout


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('logo.png'))
    apply_stylesheet(app, theme='light_blue.xml')
    window = SubtitleApp()
    window.show()
    sys.exit(app.exec())