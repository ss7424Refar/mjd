import subprocess
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QLineEdit, QMessageBox, QDialog
from psutil import NoSuchProcess
from qt_material import apply_stylesheet
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt

from gd import Ui_MainWindow
from dialog import Ui_Dialog
import sys
import os
import json
import requests
from datetime import datetime, timedelta
import api
import song
import psutil


class Dialog(QDialog, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.prefix = None
        self.K = None
        self.M = None
        self.N = None

        self.buttonBox.accepted.connect(self.on_accepted)

    def on_accepted(self):
        self.prefix = self.lineEdit.text()
        self.K = self.spinBox.value()
        self.N = self.spinBox_2.value()
        self.M = self.spinBox_3.value()

        # 获取当前进程的 PID
        faker_is_running = False
        current_pid = os.getpid()
        for proc in psutil.process_iter():
            try:
                # 获取进程的名称和 PID
                process_name = proc.name()
                process_pid = proc.pid

                # 判断进程名是否为 "faker.exe" 并且 PID 不是当前进程的 PID
                if process_name == "faker.exe" and process_pid != current_pid:
                    faker_is_running = True
                    QMessageBox.information(self, "提示", '当前数据正在执行生成中 ...')
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if not faker_is_running:
            args = ['core/faker.exe', '--K', str(self.K), '--N', str(self.N), '--M', str(self.M), '--prefix',
                    str(self.prefix + '_')]
            subprocess.Popen('cmd.exe')
            process = subprocess.Popen(args)

            QMessageBox.information(self, "提示", '开始执行 ...')


class MainWindow(QMainWindow, Ui_MainWindow):
    disable_signal = pyqtSignal()
    enable_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.timer = QTimer(self)
        self.timer1 = QTimer(self)

        lyrics_array = song.lyrics.strip().split('\n')
        self.titles = lyrics_array
        self.current_title_index = 0  # 当前标题的索引

        # 初始化数据
        self.ui_data_set = {
            "shift": {},
            "data_set": []
        }
        # 用于判断viewlist
        self.view_list = []
        # self.line_list = []
        self.execute_start_time = None
        self.runtime_str = None
        self.pid = None

        # 函数
        self.setupUi(self)
        self.ui_init()

        # 初始化流水线
        self.get_lines(self.lineEdit.text())
        self.get_shift()

        # 信号
        self.timer.timeout.connect(self.updateTitle)
        self.startTimer()

        self.radioButton.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.radioButton_2.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))

        self.lineEdit.textChanged.connect(self.on_line_changed)
        self.comboBox.activated.connect(self.get_models)
        self.comboBox.activated.connect(self.get_stations)
        self.pushButton.clicked.connect(self.stop_line)
        self.pushButton_2.clicked.connect(self.start_line)
        self.pushButton_3.clicked.connect(self.repair_system)
        self.pushButton_4.clicked.connect(self.check_ui_data)
        self.pushButton_5.clicked.connect(self.clear_data)
        self.pushButton_6.clicked.connect(self.refresh_data)

        self.actionLine.triggered.connect(open_dialog)
        self.disable_signal.connect(self.set_window_disable)
        self.enable_signal.connect(self.set_window_enable)

    def ui_init(self):
        self.label_8.setVisible(False)
        self.tableWidget_2.setColumnWidth(0, 300)
        self.tableWidget_2.setColumnWidth(1, 300)
        self.tableWidget_3.setColumnWidth(0, 300)
        self.tableWidget_3.setColumnWidth(1, 300)

        self.init_table('./data/d/', self.tableWidget_2)
        self.init_table('./data/s/', self.tableWidget_3)

        current_datetime = datetime.now()
        previous_year = current_datetime.year - 1
        updated_datetime = current_datetime.replace(year=previous_year)
        self.dateTimeEdit.setDateTime(updated_datetime)
        self.dateTimeEdit_2.setDateTime(datetime.now())

    def get_lines(self, keyword):
        try:
            url = api.my_url + ":85/mira_server_api/lines?offset=0&limit=9999"
            headers = {'Content-Type': 'application/json', 'token': api.token}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                lines = data['data']['lines']
                self.populate_pipeline_combobox(lines, keyword)
            else:
                QMessageBox.information(self, "提示", '获取流水线失败')
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def get_shift(self):
        try:
            url = api.my_url + ":85/mira_server_api/shifts/"
            headers = {'Content-Type': 'application/json', 'token': api.token}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                shifts = data['data']['shifts']
                self.populate_shifts_combobox(shifts)
            else:
                QMessageBox.information(self, "提示", '获取班次失败')
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def get_models(self):
        try:
            url = api.my_url + ":85/mira_server_api/models/selected/machine?line_id=" + str(
                self.comboBox.currentData())
            headers = {'Content-Type': 'application/json', 'token': api.token}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                models = data['data']['select_machine_model']
                self.populate_models_combobox(models)
            else:
                QMessageBox.information(self, "提示", '获取机型失败')
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def get_stations(self):
        try:
            url = api.my_url + ":85/mira_server_api/lines/" + str(
                self.comboBox.currentData()) + "/stations?offset=0&limit=9999&is_training=false"
            headers = {'Content-Type': 'application/json', 'token': api.my_url}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                stations = data['data']['stations']
                self.populate_stations_combobox(stations)
            else:
                QMessageBox.information(self, "提示", '获取工站失败')
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def on_line_changed(self):
        self.get_lines(self.lineEdit.text())

    def populate_pipeline_combobox(self, lines, keyword):
        self.comboBox.clear()

        for item in lines:
            line_id = str(item['id'])
            line_name = item['name']

            if keyword:
                if keyword in line_name:
                    display_text = f"{line_id} : {line_name}"
                    self.comboBox.addItem(display_text, item['id'])
            else:
                display_text = f"{line_id} : {line_name}"
                self.comboBox.addItem(display_text, item['id'])

    def populate_shifts_combobox(self, shifts):
        self.comboBox_2.clear()

        for item in shifts:
            shift_id = str(item['id'])
            shift_name = item['name']

            display_text = f"{shift_id} : {shift_name}"
            self.comboBox_2.addItem(display_text, item['id'])

    def populate_models_combobox(self, models):
        self.comboBox_3.clear()

        for item in models:
            model_id = str(item['machine_model_id'])
            model_name = item['machine_model_name']

            display_text = f"{model_id} : {model_name}"
            self.comboBox_3.addItem(display_text, model_id)

    def populate_stations_combobox(self, stations):
        self.comboBox_4.clear()

        for item in stations:
            station_id = str(item['id'])
            station_name = item['name']

            display_text = f"{station_id} : {station_name}"
            self.comboBox_4.addItem(display_text, station_id)

    def init_table(self, path, tableWidget):
        files = os.listdir(path)
        tableWidget.setRowCount(len(files))

        for i, file_name in enumerate(files):
            editor = QLineEdit()
            editor.setText('0')
            tableWidget.setItem(i, 0, QTableWidgetItem(str(file_name)))
            tableWidget.setCellWidget(i, 1, editor)

    def startTimer(self):
        self.timer.start(1000)  # 每隔1秒触发一次定时器

    def updateTitle(self):
        new_title = self.titles[self.current_title_index]  # 从数组获取新的标题

        self.setWindowTitle('MIRA - 故人已乘黄鹤去,不见当年练习生' + new_title)

        self.current_title_index += 1
        if self.current_title_index >= len(self.titles):
            self.current_title_index = 0

        if self.execute_start_time:
            # 计算当前的运行时间
            current_time = time.time() - self.execute_start_time

            # 将运行时间转换为小时、分钟和秒的格式
            m, s = divmod(current_time, 60)
            h, m = divmod(m, 60)
            self.runtime_str = "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))
            self.label_8.setText("运行时长：" + self.runtime_str)

            try:
                process = psutil.Process(self.pid)
            except NoSuchProcess as e:
                self.enable_signal.emit()
                return

    def check_ui_data(self):
        os.system('cls')
        # 判断开班区间
        shift_start_time = self.dateTimeEdit.dateTime().toPyDateTime()
        shift_end_time = self.dateTimeEdit_2.dateTime().toPyDateTime()

        if shift_start_time > shift_end_time:
            QMessageBox.information(self, "提示", '开始时间大于结束时间')
            return

        shift_start_hour = self.spinBox.value()
        shift_end_hour = self.spinBox_2.value()

        if shift_end_hour < shift_start_hour:
            QMessageBox.information(self, "提示", '开始[时]大于结束[时]')
            return

        line_id = self.comboBox.currentData()
        shift_id = self.comboBox_2.currentData()
        model_id = self.comboBox_3.currentData()
        station_id = self.comboBox_4.currentData()

        if line_id is None:
            QMessageBox.information(self, "提示", '请选择流水线')
            return
        if shift_id is None:
            QMessageBox.information(self, "提示", '请选择班次')
            return
        if model_id is None:
            QMessageBox.information(self, "提示", '请选择流水线-机型')
            return
        if station_id is None:
            QMessageBox.information(self, "提示", '请选择流水线-工站')
            return
        if self.radioButton.isChecked():
            dynamic = True
        else:
            dynamic = False

        ui_data = {
            "line_id": line_id,
            "shift_id": shift_id,
            "model_id": int(model_id),
            "station_id": int(station_id),
            "dynamic": dynamic,
            "files": {},
            "static_files": {}
        }

        count = self.tableWidget_2.rowCount() if dynamic else self.tableWidget_3.rowCount()
        table_widget = self.tableWidget_2 if dynamic else self.tableWidget_3
        ui_data2 = ui_data['files'] if dynamic else ui_data['static_files']
        data_type = '[动态]' if dynamic else '[静态]'

        for i in range(count):
            text = table_widget.item(i, 0).text()
            num = table_widget.cellWidget(i, 1).text()

            if not num.isdigit():
                QMessageBox.information(self, "提示", f'{data_type}以下数据不为数字 \n {text}')
                return

            if str(num).startswith('0') and len(str(num)) > 1:
                QMessageBox.information(self, "提示", f'{data_type}以下数据存在以0开头 \n {text}')
                return

            if int(num) != 0:
                ui_data2[text] = int(num)

        if dynamic:
            if not ui_data['files']:
                QMessageBox.information(self, "提示", '[动态]无模板数据')
                return
        else:
            if not ui_data['static_files']:
                QMessageBox.information(self, "提示", '[静态]无模板数据')
                return

        # 开班 要保证所有的流水线都在时间区间内
        line_str = {
            "line_id": line_id,
            "shift_id": shift_id,
            "model_id": int(model_id),
        }
        if line_str in self.view_list:
            QMessageBox.information(self, "提示", '已存在重复ViewList !')
            return
        else:
            utc_time = api.get_utc_time(api.get_local_time(shift_start_time, shift_start_hour, shift_end_hour))
            api.set_system_date(utc_time)
            result = api.force_start_shift_silent(line_id, shift_id, model_id)

            if result == -1:
                QMessageBox.information(self, "提示", '开班失败 !')
                return
            else:
                api.stop_shift_silent(line_id)
                self.view_list.append(line_str)
                # self.line_list.append(line_id)

        if self.ui_data_set["shift"] == {}:
            self.ui_data_set["shift"]["shift_start_time"] = self.dateTimeEdit.dateTime().toString('yyyy-MM-dd')
            self.ui_data_set["shift"]["shift_end_time"] = self.dateTimeEdit_2.dateTime().toString('yyyy-MM-dd')
            self.ui_data_set["shift"]["shift_start_hour"] = shift_start_hour
            self.ui_data_set["shift"]["shift_end_hour"] = shift_end_hour

        self.ui_data_set['data_set'].append(ui_data)

        content = '       '.join([data_type,
                                  self.comboBox.currentText(),
                                  self.comboBox_2.currentText(),
                                  self.comboBox_3.currentText(),
                                  self.comboBox_4.currentText()])

        self.listWidget.addItem(content)
        with open('u1.json', 'w') as file:
            file.write(json.dumps(self.ui_data_set))
        with open('v1.json', 'w') as file:
            file.write(json.dumps(self.view_list))

    def start_line(self):
        os.system('cls')
        if api.skip_view_list == 'False':
            # 判断list-widget中的有无数据
            if not self.listWidget.count() > 0:
                QMessageBox.information(self, "提示", '请选择数据后点击添加按钮 !')
                return

        if os.path.exists('u1.json') and os.path.exists('v1.json'):
            subprocess.Popen('cmd.exe')
            process = subprocess.Popen('core/main.exe')
            self.pid = process.pid
            self.execute_start_time = psutil.Process(self.pid).create_time()

            # QMessageBox.information(self, "提示", '开始执行 !')
            self.disable_signal.emit()
        else:
            QMessageBox.information(self, "提示", '请先添加数据 !')

    def stop_line(self):
        result = api.stop_shift_silent(self.comboBox.currentData())

        if result == -1:
            QMessageBox.information(self, "提示", '停班失败 !')
            return
        else:
            QMessageBox.information(self, "提示", '停班成功 !')
            return

    def repair_system(self):
        api.set_system_date(api.get_utc_time(datetime.now().strftime(api.time_format)))
        QMessageBox.information(self, "提示", "设置成功!")

    def refresh_data(self):
        self.get_lines(self.lineEdit.text())
        self.get_shift()
        QMessageBox.information(self, "提示", "刷新成功!")

    def clear_data(self):
        self.listWidget.clear()
        self.ui_data_set = {
            "shift": {},
            "data_set": []
        }
        # 用于判断viewlist
        self.view_list = []
        # self.line_list = []

        api.delete_file('v1.json')
        api.delete_file('u1.json')

    def set_window_disable(self):
        self.pushButton_2.setDisabled(True)
        self.pushButton_2.setText('请求ing')

        self.widget.setDisabled(True)
        self.label_8.setText("启动中 ...")
        self.label_8.setVisible(True)

    def set_window_enable(self):
        self.label_8.setVisible(False)

        QMessageBox.information(self, "提示", '任务完成 ~~ 时长: ' + self.runtime_str)
        self.execute_start_time = None
        self.pushButton_2.setDisabled(False)
        self.pushButton_2.setText('开班')
        self.widget.setEnabled(True)


def open_dialog():
    dialog = Dialog()
    dialog.setWindowFlags(Qt.WindowCloseButtonHint)

    dialog.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_blue.xml')

    window.setFixedSize(window.width(), window.height())
    # window.setWindowFlags(Qt.WindowMinimizeButtonHint)
    window.activateWindow()
    window.show()
    app.exec_()
