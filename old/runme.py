from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QLineEdit, QMessageBox
from qt_material import apply_stylesheet
from PyQt5.QtCore import QThread, pyqtSignal, QRunnable, QThreadPool, pyqtSlot, QTimer

from mjd import Ui_MainWindow
import sys
import os
import configparser
import json
import requests
from datetime import datetime, timedelta
import random
import time
import csv
import pytz


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.timer = QTimer(self)  # 创建定时器
        self.timer.timeout.connect(self.updateTitle)  # 连接定时器的 timeout 信号到槽函数

        self.titles = ["富强", "民主", "文明", "和谐", "自由", "平等", "公正", "法治", "爱国", "敬业", "诚信", "友善"]  # 标题数组
        self.current_title_index = 0  # 当前标题的索引
        self.startTimer()  # 启动定时器

        self.thread = JSONWriteThread()
        self.procedure_id = None
        self.sku_switch_id = None
        self.sid = None
        self.session_start_time = None

        # 创建 ConfigParser 实例
        config = configparser.ConfigParser()
        config.read('my.ini')
        self.ip = config.get('conf', 'ip')
        self.threadCount = config.get('conf', 'threadCount')
        self.my_url = "http://" + self.ip

        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(int(self.threadCount))

        self.setupUi(self)
        self.tableWidget.setColumnWidth(0, 240)
        self.tableWidget.setColumnWidth(1, 185)
        self.tableWidget_2.setColumnWidth(0, 240)
        self.tableWidget_2.setColumnWidth(1, 170)

        self.comboBox.addItem('请点击下拉数据')
        self.comboBox.activated.connect(self.get_stations)
        self.comboBox_2.activated.connect(self.set_my_data)

        self.dateTimeEdit.setDateTime(datetime.now(pytz.utc))

        # 表格初始化
        self.init_table()
        self.init_table2()

        self.pushButton_2.clicked.connect(self.get_pipeline_data)
        self.pushButton.clicked.connect(self.create_json)
        self.pushButton_3.clicked.connect(self.start_requests)
        self.thread.finished.connect(self.set_button_enable)

    def startTimer(self):
        self.timer.start(1000)  # 每隔1秒触发一次定时器

    def updateTitle(self):
        new_title = self.titles[self.current_title_index]  # 从数组获取新的标题

        self.setWindowTitle('Mira (QAQ) - (核心价值观) - ' + new_title)

        self.current_title_index += 1
        if self.current_title_index >= len(self.titles):
            self.current_title_index = 0

    def init_table(self):
        path = 'input/'
        files = os.listdir(path)
        self.tableWidget.setRowCount(len(files))

        for i, file_name in enumerate(files):
            editor = QLineEdit()
            editor.setText('0')
            self.tableWidget.setItem(i, 0, QTableWidgetItem(str(file_name)))
            self.tableWidget.setCellWidget(i, 1, editor)

    def init_table2(self):
        path = 'sinput/'
        files = os.listdir(path)
        self.tableWidget_2.setRowCount(len(files))

        for i, file_name in enumerate(files):
            editor = QLineEdit()
            editor.setText('0')
            self.tableWidget_2.setItem(i, 0, QTableWidgetItem(str(file_name)))
            self.tableWidget_2.setCellWidget(i, 1, editor)

    def get_pipeline_data(self):
        try:

            token = self.get_token()

            if token:
                url = self.my_url + ":85/mira_server_api/lines?offset=0&limit=9999"
                headers = {
                    'Content-Type': 'application/json',
                    'token': token
                }
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    data = json.loads(response.text)
                    lines = data['data']['lines']
                    self.populate_pipeline_combobox(lines)
                else:
                    show_message_box('获取流水线失败')
            else:
                show_message_box('获取token失败')
        except Exception as e:
            show_message_box(str(e))

    def get_token(self):
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
            print(str(e))
        return None

    def populate_pipeline_combobox(self, lines):
        self.comboBox.clear()

        for item in lines:
            line_id = str(item['id'])
            line_name = item['name']
            display_text = f"{line_id} : {line_name}"
            self.comboBox.addItem(display_text, item['id'])

    def populate_station_combobox(self, stations):
        self.comboBox_2.clear()
        for items in stations:
            station_id = str(items['id'])
            station_name = items['name']
            display_text = f"{station_id} : {station_name}"
            self.comboBox_2.addItem(display_text, station_id)

    def get_stations(self):
        ids = self.comboBox.currentData()
        token = self.get_token()

        try:
            if token:
                url2 = self.my_url + ":85/mira_server_api/lines/" + str(
                    ids) + "/stations?offset=0&limit=9999&is_training=false"
                headers = {
                    'Content-Type': 'application/json',
                    'token': token
                }
                response = requests.get(url2, headers=headers)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    stations = data['data']['stations']
                    self.populate_station_combobox(stations)
                else:
                    show_message_box('获取工站失败')
            else:
                show_message_box('获取token失败')
        except Exception as e:
            show_message_box(str(e))

    def set_my_data(self):
        # 发送请求
        self.sid = self.comboBox_2.currentData()
        token = self.get_token()
        try:
            if token:
                url3 = self.my_url + ":85/mira_server_api/client/config/" + str(self.sid)
                headers = {'Content-Type': 'application/json', 'token': token}
                response = requests.get(url3, headers=headers)
                if response.status_code == 200:
                    data3 = json.loads(response.text)
                    if 'data' in data3 and data3['data'] is not None and 'procedure_id' in data3['data']:
                        self.procedure_id = data3['data']['procedure_id']
                    else:
                        show_message_box('获取procedure_id失败-sendData')
                else:
                    show_message_box('获取procedure_id失败')

                url4 = self.my_url + ":85/mira_server_api/client/production_status/" + str(self.sid)
                response = requests.request("GET", url4, headers=headers)
                if response.status_code == 200:
                    data4 = json.loads(response.text)
                    if 'data' in data4 and data4['data'] is not None and 'sku_switch_id' in data4['data']:
                        self.sku_switch_id = data4['data']['sku_switch_id']
                    else:
                        show_message_box('获取sku_switch_id失败-sendData')

                else:
                    show_message_box('获取sku_switch_id失败')
            else:
                show_message_box('获取token失败')
        except Exception as e:
            show_message_box(str(e))

        self.label.setText('sku_switch: {},  procedure: {}'.format(str(self.sku_switch_id), str(self.procedure_id)))

    def create_json(self):
        if self.procedure_id is None or self.sku_switch_id is None:
            show_message_box('初始化参数缺失')
            return
        # 获取表格1中的值
        count = self.tableWidget.rowCount()
        for i in range(count):
            text = self.tableWidget.item(i, 0).text()
            num = self.tableWidget.cellWidget(i, 1).text()
            if not num.isdigit():
                show_message_box('[动态]以下数据不为数字 \n {}'.format(text))
                return
            if str(num).startswith('0') and len(str(num)) > 1:
                show_message_box('[动态]以下数据存在以0开头 \n {}'.format(text))
                return

        # 获取表格2中的值
        count2 = self.tableWidget_2.rowCount()
        for i in range(count2):
            text = self.tableWidget_2.item(i, 0).text()
            num = self.tableWidget_2.cellWidget(i, 1).text()
            if not num.isdigit():
                show_message_box('[静态]以下数据不为数字 \n {}'.format(text))
                return
            if str(num).startswith('0') and len(str(num)) > 1:
                show_message_box('[静态]以下数据存在以0开头 \n {}'.format(text))
                return

        # 生成初始化文件
        data = {
            "session_start_time": self.dateTimeEdit.dateTime().toString('yyyy-MM-dd hh:mm:ss'),
            "sku_switch_id": self.sku_switch_id,
            "procedure_id": self.procedure_id,
            "line_id": self.comboBox.currentData(),
            "station_id": self.comboBox_2.currentData(),
            "files": {},
            "static_files": {}
        }
        for i in range(count):
            text = self.tableWidget.item(i, 0).text()
            num = self.tableWidget.cellWidget(i, 1).text()
            if int(num) == 0:
                continue
            else:
                data['files'][text] = int(num)

        # 静态数据
        for i in range(count2):
            text = self.tableWidget_2.item(i, 0).text()
            num = self.tableWidget_2.cellWidget(i, 1).text()
            if int(num) == 0:
                continue
            else:
                data['static_files'][text] = int(num)

        with open("init.json", "w") as file:
            json.dump(data, file, indent=4)

        self.thread.start()
        self.set_button_disable()

    def set_button_disable(self):
        self.pushButton.setDisabled(True)
        self.pushButton.setText('生成ing')
        # show_message_box('请耐心等待文件生成')

    def set_button_enable(self):
        self.pushButton.setDisabled(False)
        self.pushButton.setText('生成JSON')
        show_message_box('我已经生成文件啦啦啦~~~')

    def set_window_disable(self):
        self.pushButton_3.setDisabled(True)
        self.pushButton_3.setText('请求ing')
        self.widget_2.setDisabled(True)

    def set_window_enable(self):
        self.pushButton_3.setDisabled(False)
        self.pushButton_3.setText('发送请求')
        self.widget_2.setEnabled(True)

    def start_requests(self):
        if self.sid is None:
            show_message_box('请先选择生成json再发送请求')
            return

        dir = 'output/'
        print('')
        print('>>>>> starting request ...\n')
        for tf in os.listdir(dir):
            if tf.startswith('exception'):
                with open(dir + tf, 'r', encoding='utf8', errors='ignore') as f:
                    json_content = json.load(f)
                    # 创建任务实例
                    task = RequestTask(self.my_url + ':85/mira_server_api/client/exception_time',
                                       json_content, '[dynamic-exception] ' + tf)
                    # 启动任务
                    self.threadpool.start(task)
            else:
                with open(dir + tf, 'r', encoding='utf8', errors='ignore') as f:
                    json_content = json.load(f)
                    # 创建任务实例
                    task = RequestTask(
                        self.my_url + ':85/mira_server_api/client/detect_result/dynamic/' + str(self.sid),
                        json_content, '[dynamic] ' + tf)
                    # 启动任务
                    self.threadpool.start(task)

        dir = 'soutput/'
        for tf in os.listdir(dir):
            with open(dir + tf, 'r', encoding='utf8', errors='ignore') as f:
                json_content = json.load(f)
                json_content = self.rebuild_json(json_content)
                # 创建任务实例
                task = RequestTask(self.my_url + ':85/mira_server_api/client/detect_result/static/' + str(self.sid),
                                   json_content, '[static] ' + tf)
                # 启动任务
                self.threadpool.start(task)

        self.set_window_disable()
        show_message_box('请耐心等待请求结束')
        QTimer.singleShot(0, self.check_tasks_finished)

    def check_tasks_finished(self):
        active_thread_count = self.threadpool.activeThreadCount()
        if active_thread_count == 0:
            self.set_window_enable()
            # 所有任务完成后的操作
            show_message_box("完成所有请求啦啦啦 ~~~")
        else:
            # 继续等待任务完成
            QTimer.singleShot(1000, self.check_tasks_finished)

    def rebuild_json(self, json_data):
        if json_data["OverallResult"] == "OK":
            temp_over_result = 0
        else:
            temp_over_result = 32
        temp = {"na_model_id": 0, "session_index": 0, "sop_id": "", 'attendant_time': 1,
                'operation_time': 1, 'procedure_id': self.procedure_id,
                'session_end_time': json_data["EndTimeText"], 'session_start_time': json_data["StartTimeText"],
                'sku_switch_id': self.sku_switch_id, 'sn_no': json_data["SNNumebrText"], 'ng_summary': temp_over_result}

        json_data['ImagePath'] = None
        temp['result_static_detail'] = str(json_data)
        return temp


class JSONWriteThread(QThread):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(JSONWriteThread, self).__init__(parent)

    def run(self):
        copy_json_file()
        self.finished.emit()


class RequestTask(QRunnable):
    def __init__(self, url, json_data, tf):
        super().__init__()
        self.url = url
        self.json_data = json_data
        self.tf = tf

    @pyqtSlot()
    def run(self):
        # try:
        response = requests.post(self.url, json=self.json_data)
        # QCoreApplication.processEvents()
        # time.sleep(1000)
        print(self.tf + ' ==> ' + response.text + '\n')
        # except:
        #     print(111)
        # except Exception as e:
        #     print(e)


def copy_json_file():
    clear_folder('output')
    clear_folder('soutput')

    # 从文件中读取JSON数据
    with open('init.json', 'r') as file:
        json_data = file.read()

    # 解析JSON数据
    config = json.loads(json_data)
    session_start_time = config["session_start_time"]
    files = config["files"]
    static_files = config["static_files"]

    os.system('cls')
    all_csv = 'gd_ng_summary-' + str(int(time.time())) + '.csv'
    if len(files) > 0:
        print('>>>>> create dynamic files ... \n')
    for filename, value in files.items():
        for i in range(value):
            # print('next start time {}'.format(session_start_time))
            session_end_time_str = write_json(filename, session_start_time, config, i, all_csv)
            session_start_time = session_end_time_str

    if len(static_files) > 0:
        print('\n')
        print('>>>>> create static files ... \n')
    for filename, value in static_files.items():
        for i in range(value):
            print('creating files ... {}-{}'.format(filename, i))
            session_next_time_str = write_static_json(filename, session_start_time, i)
            session_start_time = session_next_time_str


def write_json(filename, session_start_time, config, i, all_csv):
    index = filename.split('-')[1].replace('.json', '')
    if int(index) < 4:
        operation_time = random.randint(56, 65)
        attendant_time = random.randint(1, 10)
    else:
        operation_time = random.randint(66, 80)
        attendant_time = random.randint(21, 30)

    file_path = './input/' + filename
    output_name = filename.split('.')[0] + '_' + str(i) + '.json'
    new_file_path = './output/' + output_name
    all_file_path = './' + all_csv

    # 检查文件是否存在
    if not os.path.isfile(all_file_path):
        print('save gd to ... ' + all_file_path)
        # 文件不存在，创建新文件并写入表头
        with open(all_file_path, 'a', newline='', encoding='utf8', errors='ignore') as file:
            writer = csv.writer(file)
            header = ['文件名', 'operation time', 'attendant time']
            writer.writerow(header)

    # 读取原始JSON数据
    with open(file_path, 'r', encoding='utf8', errors='ignore') as file:
        json_data = file.read()

    # 解析JSON数据
    data = json.loads(json_data)

    data["session_start_time"] = session_start_time
    data["operation_time"] = str(operation_time) + '000'
    data["attendant_time"] = attendant_time
    data["sku_switch_id"] = config["sku_switch_id"]
    data["procedure_id"] = config["procedure_id"]

    global sno
    data["sn_no"] = str(sno).zfill(7)
    sno = sno + 1

    time_format = "%Y-%m-%d %H:%M:%S"
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
        print('creating files ... {}'.format(output_name))
        file.write(new_json_data)

    # 创建exception文件
    exception_time = operation_time + attendant_time - 80
    if exception_time > 0:
        exception_data = {
            "line_id": config['line_id'],
            "station_id": config['station_id'],
            "exception_time": exception_time
        }
        new_path = './output/' + 'exception_' + output_name
        et = json.dumps(exception_data, indent=4, ensure_ascii=False)
        with open(new_path, 'w', encoding='utf8', errors='ignore') as file:
            print('creating files ... {}'.format('exception_' + output_name))
            file.write(et)

    with open(all_file_path, 'a', newline='', encoding='utf8', errors='ignore') as f:
        data = [output_name, str(operation_time * 1000), str(attendant_time)]
        writer = csv.writer(f)
        writer.writerow(data)

    return session_end_time_str


def write_static_json(filename, session_start_time, i):
    file_path = './sinput/' + filename
    new_file_path = './soutput/' + filename.split('.')[0] + '_' + str(i) + '.json'

    # 读取原始JSON数据
    with open(file_path, 'r', encoding='utf8', errors='ignore') as file:
        json_data = file.read()

    # 解析JSON数据
    data = json.loads(json_data)

    global sno2
    data["StartTimeText"] = session_start_time
    data["SNNumebrText"] = str(sno2).zfill(7)
    sno2 = sno2 + 1

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
    return next_start_time_str


def show_message_box(msg):
    QMessageBox.information(window, "提示", msg)


def clear_folder(dir):
    for f in os.listdir(dir):
        os.remove(os.path.join(dir, f))


if __name__ == '__main__':
    clear_folder('output')
    clear_folder('soutput')

    sno = 1
    sno2 = 1

    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_blue.xml')

    window.setFixedSize(window.width(), window.height())
    # window.setWindowFlags(Qt.WindowMinimizeButtonHint)
    window.activateWindow()
    window.show()
    app.exec_()
