import time

from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QLineEdit, QMessageBox
from qt_material import apply_stylesheet
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

from gd import Ui_MainWindow
import sys
import os
import configparser
import json
import requests
from datetime import datetime, timedelta
import random
import csv
import paramiko
import pytz


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.thread = None
        self.timer = QTimer(self)

        lyrics = """
        鸡你太美 baby 鸡你太美 baby
        鸡你实在是太美 baby 鸡你太美 baby
        迎面走来的你让我如此蠢蠢欲动
        这种感觉我从未有
        Cause I got a crush on you who you
        你是我的我是你的谁
        再多一眼看一眼就会爆炸
        再近一点靠近点快被融化
        想要把你占为己有baby bae
        不管走到哪里都会想起的人是你 you you
        我应该拿你怎样
        uh 所有人都在看着你
        我的心总是不安
        oh 我现在已病入膏肓
        eh eh 难道真的因为你而疯狂吗
        我本来不是这种人
        因你变成奇怪的人
        第一次呀变成这样的我
        不管我怎么去否认
        鸡你太美 baby 鸡你太美 baby
        鸡你实在是太美 baby 鸡你太美 baby
        oh eh oh 现在确认地告诉我
        oh eh oh 你到底属于谁
        oh eh oh 现在确认地告诉我
        oh eh oh 你到底属于谁 就是现在告诉我
        跟着这节奏 缓缓 make wave
        甜蜜的奶油 it"s your birthday cake
        男人们的 game call me 你恋人
        别被欺骗愉快的 I wanna play
        我的脑海每分每秒只为你一人沉醉
        最迷人让我神魂颠倒是你身上香水
        oh right baby I"m fall in love with you
        我的一切你都拿走只要有你就已足够
        我到底应该怎样
        uh 我心里一直很不安
        其他男人们的视线
        Oh 全都只看向你的脸
        Eh eh 难道真的因为你而疯狂吗
        我本来不是这种人
        因你变成奇怪的人
        第一次呀变成这样的我
        不管我怎么去否认
        鸡你太美 baby 鸡你太美 baby
        鸡你实在是太美 baby 鸡你太美 baby
        我愿意把我的全部都给你
        我每天在梦里都梦见你还有我闭着眼睛也能看到你
        现在开始我只准你看我
        I don’t wanna wake up in dream 我只想看你这是真心话
        鸡你太美 baby 鸡你太美 baby
        鸡你实在是太美 baby 鸡你太美 baby
        oh eh oh 现在确认的告诉我
        oh eh oh 你到底属于谁
        oh eh oh 现在确认的告诉我
        oh eh oh 你到底属于谁就是现在告诉我
        """

        lyrics_array = lyrics.strip().split('\n')
        self.titles = lyrics_array
        self.current_title_index = 0  # 当前标题的索引

        # 初始化数据
        self.ip = None
        self.username = None
        self.password = None
        self.port = None
        self.my_url = None
        self.session_begin = None
        self.ui_data = None
        self.work_path = None
        self.execute_start_time = None
        self.runtime_str = None

        # 函数
        self.setupUi(self)
        self.ui_init()
        self.env_init()
        self.token = self.init_token()

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
        self.pushButton.clicked.connect(lambda: self.stop_shift(self.comboBox.currentData()))
        self.pushButton_2.clicked.connect(self.check_ui_data)
        self.pushButton_3.clicked.connect(lambda: self.repair_system('2022-11-22 06:06:06'))
        # self.pushButton_4.clicked.connect(self.add_station)

    def ui_init(self):
        self.label_8.setVisible(False)
        self.tableWidget_2.setColumnWidth(0, 300)
        self.tableWidget_2.setColumnWidth(1, 300)
        self.tableWidget_3.setColumnWidth(0, 300)
        self.tableWidget_3.setColumnWidth(1, 300)

        self.init_table('../data/d/', self.tableWidget_2)
        self.init_table('../data/s/', self.tableWidget_3)

        current_datetime = datetime.now()
        previous_year = current_datetime.year - 1
        updated_datetime = current_datetime.replace(year=previous_year)
        self.dateTimeEdit.setDateTime(updated_datetime)
        self.dateTimeEdit_2.setDateTime(datetime.now())

    def env_init(self):
        config = configparser.ConfigParser()
        config.read('my.ini')
        self.ip = config.get('conf', 'ip')
        self.username = config.get('conf', 'username')
        self.password = config.get('conf', 'password')
        self.port = config.get('conf', 'port')
        self.session_begin = config.get('conf', 'session_begin')
        self.my_url = "http://" + self.ip

    def init_token(self):
        url = self.my_url + ":8084/system_management_api/LoginController/login"
        payload = json.dumps({
            "name": "admin",
            "password": "E10ADC3949BA59ABBE56E057F20F883E"
        })
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, data=payload)
            if response.status_code == 200:
                data = json.loads(response.text)
                return data['data']['token']
        except Exception as e:
            print('初始化获取token失败 - ' + str(e))
            QMessageBox.information(self, "提示", str(e))
        return None

    def get_lines(self, keyword):
        try:
            url = self.my_url + ":85/mira_server_api/lines?offset=0&limit=9999"
            headers = {'Content-Type': 'application/json', 'token': self.token}
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
            url = self.my_url + ":85/mira_server_api//shifts/"
            headers = {'Content-Type': 'application/json', 'token': self.token}
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
            url = self.my_url + ":85/mira_server_api/models/selected/machine?line_id=" + str(
                self.comboBox.currentData())
            headers = {'Content-Type': 'application/json', 'token': self.token}
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
            url = self.my_url + ":85/mira_server_api/lines/" + str(
                self.comboBox.currentData()) + "/stations?offset=0&limit=9999&is_training=false"
            headers = {'Content-Type': 'application/json', 'token': self.token}
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

        self.ui_data = {
            "shift_start_time": self.dateTimeEdit.dateTime().toString('yyyy-MM-dd'),
            "shift_end_time": self.dateTimeEdit_2.dateTime().toString('yyyy-MM-dd'),
            "shift_start_hour": shift_start_hour,
            "shift_end_hour": shift_end_hour,
            "line_id": line_id,
            "shift_id": shift_id,
            "model_id": int(model_id),
            "station_id": int(station_id),
            "dynamic": dynamic,
            "files": {},
            "static_files": {}
        }

        count = self.tableWidget_2.rowCount() if dynamic else self.tableWidget_3.rowCount()
        tableWidget = self.tableWidget_2 if dynamic else self.tableWidget_3
        ui_data = self.ui_data['files'] if dynamic else self.ui_data['static_files']
        data_type = '[动态]' if dynamic else '[静态]'

        for i in range(count):
            text = tableWidget.item(i, 0).text()
            num = tableWidget.cellWidget(i, 1).text()

            if not num.isdigit():
                QMessageBox.information(self, "提示", f'{data_type}以下数据不为数字 \n {text}')
                return

            if str(num).startswith('0') and len(str(num)) > 1:
                QMessageBox.information(self, "提示", f'{data_type}以下数据存在以0开头 \n {text}')
                return

            if int(num) != 0:
                ui_data[text] = int(num)

        if dynamic:
            if not self.ui_data['files']:
                QMessageBox.information(self, "提示", '[动态]无模板数据')
                return
        else:
            if not self.ui_data['static_files']:
                QMessageBox.information(self, "提示", '[静态]无模板数据')
                return

        self.start_shift()

    def start_shift(self):
        try:
            url = self.my_url + ":85/mira_server_api/lines/" + str(
                self.comboBox.currentData()) + "/can_start?shift_id=" + \
                  str(self.comboBox_2.currentData()) + "&model_id=" + str(self.comboBox_3.currentData())

            headers = {'Content-Type': 'application/json', 'token': self.token}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                can_start = data['data']['can_start']

                if not can_start:
                    reply = QMessageBox.question(self, '确认', '是否强制开班?', QMessageBox.Yes | QMessageBox.No,
                                                 QMessageBox.No)

                    if reply == QMessageBox.Yes:
                        self.force_start_shift()
            else:
                QMessageBox.information(self, "提示", '开班失败')
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def force_start_shift(self):
        try:
            url = self.my_url + ":85/mira_server_api/lines/" + str(self.comboBox.currentData()) + "/switch"

            headers = {'Content-Type': 'application/json', 'token': self.token}
            payload = json.dumps({
                "shift_id": str(self.comboBox_2.currentData()),
                "model_id": str(self.comboBox_3.currentData()),
                "start_now": True,
                "time_zone": 8
            })
            response = requests.put(url, payload, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                code = data['code']
                if code == 409:
                    QMessageBox.information(self, "提示", '强制开班失败(409)\n' + data['message'])
                else:
                    result = self.stop_shift_silent(self.ui_data['line_id'])
                    if result == 0:
                        self.set_window_disable()
                        self.thread = WorkerThread()
                        self.thread.finished.connect(self.on_finished)
                        self.thread.start()

                        # self.generate_data()
            else:
                QMessageBox.information(self, "提示", '强制开班失败')
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def stop_shift(self, line_id):
        try:
            url = self.my_url + ":85/mira_server_api/lines/" + str(line_id) + "/stop"

            headers = {'Content-Type': 'application/json', 'token': self.token}
            response = requests.put(url, headers=headers)
            data = json.loads(response.text)
            if response.status_code == 200:
                if data['code'] == 200:
                    QMessageBox.information(self, "提示", '停班成功')
                else:
                    QMessageBox.information(self, "提示", '停班失败\n' + data['message'])
            else:
                QMessageBox.information(self, "提示", '停班失败\n' + data['message'])
        except Exception as e:
            QMessageBox.information(self, "提示", str(e))

    def stop_shift_silent(self, line_id):
        try:
            url = self.my_url + ":85/mira_server_api/lines/" + str(line_id) + "/stop"
            headers = {'Content-Type': 'application/json', 'token': self.token}
            response = requests.put(url, headers=headers)
            data = json.loads(response.text)
            if response.status_code == 200:
                if data['code'] == 200:
                    print('静默停班成功')
                    return 0
                else:
                    print('静默停班失败 ' + data['message'])
                    return -1
            else:
                print('静默停班失败 ' + data['message'])
                return -1
        except Exception as e:
            print('静默停班失败 ' + str(e))
            return -1
        finally:
            print()
            print()
            print()

    def repair_system(self, sys_time):
        self.set_system_date(sys_time)
        QMessageBox.information(self, "提示", "设置成功!")

    def set_system_date(self, sys_time):
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(self.ip, self.port, self.username,
                           self.password)

        # 执行修改系统时间的命令 2023-12-28 14:49:00
        stdin, stdout, stderr = ssh_client.exec_command('sudo date -s "' + sys_time + '"')
        # 输出命令执行结果
        print('设置系统时间为: ' + sys_time + '_' + stdout.read().decode('utf-8').strip())
        ssh_client.close()

    # def add_station(self):




    def on_finished(self):
        self.set_window_enable()

    def set_window_disable(self):
        self.pushButton_2.setDisabled(True)
        self.pushButton_2.setText('请求ing')
        self.widget.setDisabled(True)

        self.execute_start_time = time.time()
        self.label_8.setVisible(True)

    def set_window_enable(self):
        self.label_8.setVisible(False)
        self.execute_start_time = None

        QMessageBox.information(self, "提示", '任务完成 ~~ 时长: ' + self.runtime_str)
        self.pushButton_2.setDisabled(False)
        self.pushButton_2.setText('开班')
        self.widget.setEnabled(True)


class WorkerThread(QThread):
    finished = pyqtSignal()


    def __init__(self):
        super().__init__()
        self.work_path = None
        self.main_window = None

    def run(self):
        main_window = QApplication.instance().activeWindow()
        if main_window is not None:
            self.main_window = main_window
            self.generate_data()
            self.finished.emit()

    def generate_data(self):
        current_time = datetime.now()
        folder_name = current_time.strftime("%Y%m%d%H%M%S")
        self.work_path = './data/o/' + folder_name + '/'
        os.makedirs(self.work_path, exist_ok=True)

        start_day = datetime.strptime(self.main_window.ui_data['shift_start_time'], "%Y-%m-%d")
        end_day = datetime.strptime(self.main_window.ui_data['shift_end_time'], "%Y-%m-%d")

        shanghai_tz = pytz.timezone('Asia/Shanghai')
        while start_day <= end_day:
            random_hour = random.randint(int(self.main_window.ui_data['shift_start_hour']),
                                         int(self.main_window.ui_data['shift_end_hour']))
            random_minute = random.randint(0, 59)

            set_system_time = start_day.strftime("%Y-%m-%d") + " {:02d}:{:02d}:00".format(random_hour, random_minute)
            set_system_time_dt = datetime.strptime(set_system_time, "%Y-%m-%d %H:%M:%S")
            utc_time = shanghai_tz.localize(set_system_time_dt).astimezone(pytz.timezone('UTC')).strftime(
                "%Y-%m-%d %H:%M:%S")

            self.main_window.set_system_date(utc_time)
            result = self.force_start_shift_silent()

            if result == 0:
                # 获取sku_switch以及procedure_id接口
                self.get_sku_procedure_id(set_system_time)
                self.main_window.stop_shift_silent(self.main_window.ui_data['line_id'])
            else:
                break
            start_day = start_day + timedelta(days=1)

    def force_start_shift_silent(self):
        try:
            url = self.main_window.my_url + ":85/mira_server_api/lines/" + \
                  str(self.main_window.comboBox.currentData()) + "/switch"

            headers = {'Content-Type': 'application/json', 'token': self.main_window.token}
            payload = json.dumps({
                "shift_id": self.main_window.ui_data['shift_id'],
                "model_id": self.main_window.ui_data['model_id'],
                "start_now": True,
                "time_zone": 8
            })
            response = requests.put(url, payload, headers=headers)

            if response.status_code == 200:
                data = json.loads(response.text)
                if data['code'] == 409:
                    print('静默强制开班失败(409) ' + data['message'])
                    return -1
                else:
                    print('静默强制开班成功')
                    return 0
            else:
                print('静默强制开班失败')
                return -1
        except Exception as e:
            print('静默强制开班失败' + str(e))
            return -1

    def get_sku_procedure_id(self, utc_time):
        try:
            # url1 = None
            # if self.ui_data['dynamic']:
            #     url1 = self.my_url + ":85/mira_server_api/client/operation/config/" + str(self.ui_data['station_id'])
            # else:
            #     url1 = self.my_url + ":85/mira_server_api/client/defect/config/" + str(self.ui_data['station_id'])

            url = self.main_window.my_url + ":85/mira_server_api/client/production_status/" + \
                  str(self.main_window.ui_data['station_id'])
            response = requests.request("GET", url, headers={'Content-Type': 'application/json',
                                                             'token': self.main_window.token})
            if response.status_code == 200:
                data = json.loads(response.text)
                if data['code'] == 200:
                    procedure_id = data['data']['procedures'][0]['procedure_id']
                    sku_switch_id = data['data']['sku_switch_id']
                    if self.main_window.ui_data['dynamic']:
                        self.write_dynamic_json(procedure_id, sku_switch_id, utc_time)
                    else:
                        self.write_static_json(procedure_id, sku_switch_id, utc_time)
                else:
                    print('获取sku_procedure失败~')
            else:
                print('获取sku_procedure失败')
        except Exception as e:
            print('get sku_procedure失败 ' + str(e))

    def write_dynamic_json(self, procedure_id, sku_switch_id, session_start_time):
        files = self.main_window.ui_data['files']
        time_format = "%Y-%m-%d %H:%M:%S"
        session_start_time = (datetime.strptime(session_start_time, time_format) +
                              timedelta(seconds=int(self.main_window.session_begin))).strftime(time_format)
        print('文件路径: ' + self.work_path)
        sno = 1
        for filename, value in files.items():
            save_file = []

            ymd = datetime.strptime(session_start_time, time_format).strftime('%Y%m%d')
            for i in range(value):
                index = filename.split('-')[1].replace('.json', '')
                if int(index) < 4:
                    operation_time = random.randint(56, 65)
                    attendant_time = random.randint(1, 10)
                else:
                    operation_time = random.randint(66, 80)
                    attendant_time = random.randint(21, 30)

                origin_file_path = './data/d/' + filename
                output_name = filename.split('.')[0] + '_' + ymd + '_' + str(i) + '.json'
                new_file_path = self.work_path + output_name
                save_file.append(new_file_path)

                # 读取原始JSON数据
                with open(origin_file_path, 'r', encoding='utf8', errors='ignore') as file:
                    json_data = file.read()

                # 解析JSON数据
                data = json.loads(json_data)

                data["session_start_time"] = session_start_time
                data["operation_time"] = str(operation_time) + '000'
                data["attendant_time"] = attendant_time
                data["sku_switch_id"] = sku_switch_id
                data["procedure_id"] = procedure_id

                data["sn_no"] = str(sno).zfill(7)
                sno = sno + 1

                original_time = datetime.strptime(session_start_time, time_format)
                end_time = original_time + timedelta(seconds=operation_time)
                start_time = end_time - timedelta(seconds=10)
                session_end_time = end_time + timedelta(seconds=attendant_time)
                # 格式化新的时间
                start_time_str = start_time.strftime(time_format)
                end_time_str = end_time.strftime(time_format)
                session_end_time_str = session_end_time.strftime(time_format)

                data["result_detail"]["startTime"] = start_time_str
                data["result_detail"]["endTime"] = end_time_str
                data["session_end_time"] = session_end_time_str
                data["result_detail"]["operationTime"] = str(operation_time) + '000'

                # 生成新的JSON
                new_json_data = json.dumps(data, indent=4, ensure_ascii=False)

                # 写入新的JSON文件
                with open(new_file_path, 'w', encoding='utf8', errors='ignore') as file:
                    # print('creating files ... {}'.format(output_name))
                    file.write(new_json_data)

                session_start_time = session_end_time_str

            # 发送请求
            self.send_dynamic_request(save_file)

    def write_static_json(self, procedure_id, sku_switch_id, session_start_time):
        static_files = self.main_window.ui_data['static_files']
        time_format = "%Y-%m-%d %H:%M:%S"
        session_start_time = (datetime.strptime(session_start_time, time_format) +
                              timedelta(seconds=int(self.main_window.session_begin))).strftime(time_format)
        print('文件路径: ' + self.work_path)
        sno = 1
        for filename, value in static_files.items():
            save_file = []

            ymd = datetime.strptime(session_start_time, time_format).strftime('%Y%m%d')
            for i in range(value):
                file_path = './data/s/' + filename
                new_file_path = self.work_path + filename.split('.')[0] + '_' + ymd + '_' + str(i) + '.json'
                save_file.append(new_file_path)

                # 读取原始JSON数据
                with open(file_path, 'r', encoding='utf8', errors='ignore') as file:
                    json_data = file.read()

                # 解析JSON数据
                data = json.loads(json_data)

                data["StartTimeText"] = session_start_time
                data["SNNumebrText"] = str(sno).zfill(7)
                sno = sno + 1

                time_format = "%Y-%m-%d %H:%M:%S"
                original_time = datetime.strptime(session_start_time, time_format)
                end_time = original_time + timedelta(seconds=1)
                next_start_time = original_time + timedelta(seconds=3)

                # 格式化新的时间
                end_time_str = end_time.strftime(time_format)
                next_start_time_str = next_start_time.strftime(time_format)
                data["EndTimeText"] = end_time_str
                data["timeTip"] = str(original_time) + '-' + end_time_str

                # 生成新的JSON文件
                new_json_data = json.dumps(data, indent=4, ensure_ascii=False)

                # 写入新的JSON文件
                with open(new_file_path, 'w', encoding='utf8', errors='ignore') as file:
                    file.write(new_json_data)

                file.close()
                session_start_time = next_start_time_str

            self.send_static_request(save_file, procedure_id, sku_switch_id)

    def send_dynamic_request(self, save_file):
        for file_path in save_file:
            with open(file_path, 'r', encoding='utf8', errors='ignore') as f:
                json_content = json.load(f)
            try:
                url = self.main_window.my_url + ":85/mira_server_api/client/detect_result/dynamic/" + str(
                    self.main_window.ui_data['station_id'])
                response = requests.request("POST", json=json_content, url=url,
                                            headers={'Content-Type': 'application/json',
                                                     'token': self.main_window.token})
                data = json.loads(response.text)
                if response.status_code == 200:
                    if data['code'] == 200:
                        print(' > ' +
                              os.path.basename(file_path) + ' - 发送动态检测请求成功~ ' + data['data']['message'])
                    else:
                        print('发送动态检测请求失败~')
                else:
                    print('发送动态检测请求失败')
            except Exception as e:
                print('发送动态检测请求失败 ' + str(e))

    def send_static_request(self, save_file, procedure_id, sku_switch_id):
        for file_path in save_file:
            with open(file_path, 'r', encoding='utf8', errors='ignore') as f:
                json_content = json.load(f)
                json_content = rebuild_json(json_content, procedure_id, sku_switch_id)
            try:
                url = self.main_window.my_url + ":85/mira_server_api/client/detect_result/static/" + \
                      str(self.main_window.ui_data['station_id'])
                response = requests.request("POST", json=json_content, url=url,
                                            headers={'Content-Type': 'application/json',
                                                     'token': self.main_window.token})
                data = json.loads(response.text)
                if response.status_code == 200:
                    if data['code'] == 200:
                        print(' > ' +
                              os.path.basename(file_path) + ' - 发送静态检测请求成功~ ' + data['data']['message'])
                    else:
                        print('发送静态检测请求失败~')
                else:
                    print('发送静态检测请求失败')
            except Exception as e:
                print('发送静态检测请求失败 ' + str(e))


def rebuild_json(json_data, procedure_id, sku_switch_id):
    if json_data["OverallResult"] == "OK":
        temp_over_result = 0
    else:
        temp_over_result = 32
    temp = {"na_model_id": 0, "session_index": 0, "sop_id": "", 'attendant_time': 1, 'operation_time': 1,
            'procedure_id': procedure_id, 'session_end_time': json_data["EndTimeText"],
            'session_start_time': json_data["StartTimeText"], 'sku_switch_id': sku_switch_id,
            'sn_no': json_data["SNNumebrText"], 'ng_summary': temp_over_result}

    json_data['ImagePath'] = None
    temp['result_static_detail'] = str(json_data)
    return temp


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='light_cyan.xml')

    window.setFixedSize(window.width(), window.height())
    # window.setWindowFlags(Qt.WindowMinimizeButtonHint)
    window.activateWindow()
    window.show()
    app.exec_()
