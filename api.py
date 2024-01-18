import os
import configparser
import json

import psutil
import requests
from datetime import datetime, timedelta
import random
import paramiko
import pytz
import traceback
import time


def get_utc_time(session_start):
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    set_system_time_dt = datetime.strptime(session_start, "%Y-%m-%d %H:%M:%S")
    utc_time = shanghai_tz.localize(set_system_time_dt).astimezone(pytz.timezone('UTC')).strftime(
        "%Y-%m-%d %H:%M:%S")

    return utc_time


def get_local_time(shift_start_time, shift_start_hour, shift_end_hour):
    random_hour = random.randint(int(shift_start_hour), int(shift_end_hour))
    random_minute = random.randint(0, 59)

    set_system_time = shift_start_time.strftime("%Y-%m-%d") + " {:02d}:{:02d}:00".format(random_hour, random_minute)
    return set_system_time


def set_system_date(sys_time):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(ip, int(port), username, password)

    # 执行修改系统时间的命令 2023-12-28 14:49:00
    stdin, stdout, stderr = ssh_client.exec_command('sudo date -s "' + sys_time + '"')
    # 输出命令执行结果
    print('设置系统时间为: ' + sys_time + '_' + stdout.read().decode('utf-8').strip())
    ssh_client.close()


def init_token():
    url = my_url + ":8084/system_management_api/LoginController/login"
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
    return None


def force_start_shift_silent(line_id, shift_id, model_id):
    try:
        url = my_url + ":85/mira_server_api/lines/" + str(line_id) + "/switch"

        headers = {'Content-Type': 'application/json', 'token': token}
        payload = json.dumps({
            "shift_id": shift_id,
            "model_id": model_id,
            "start_now": True,
            "time_zone": 8
        })
        response = requests.put(url, payload, headers=headers)

        if response.status_code == 200:
            data = json.loads(response.text)
            if data['code'] == 409:
                print("流水线 - [{}] 强制开班失败(409) {}".format(line_id, data['message']))
                return -1
            else:
                print("流水线 - [{}] 静默强制开班成功".format(line_id))
                return 0
        else:
            print("流水线 - [{}] 强制开班失败 - {}/ {}".format(line_id, response.status_code, response.text))
            return -1
    except Exception as e:
        print("流水线 - [{}] 强制开班失败 {}".format(line_id, str(e)))
        return -1


def stop_shift_silent(line_id):
    try:
        url = my_url + ":85/mira_server_api/lines/" + str(line_id) + "/stop"
        headers = {'Content-Type': 'application/json', 'token': token}
        response = requests.put(url, headers=headers)
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print("流水线 - [{}] 静默停班成功".format(line_id))
                return 0
            else:
                print("流水线 - [{}] 静默停班失败 {}".format(line_id, data['message']))
                return -1
        else:
            print("流水线 - [{}] 静默停班失败& {}".format(line_id, data['message']))
            return -1
    except Exception as e:
        print("流水线 - [{}] 静默停班失败 {}".format(line_id, str(e)))
        return -1
    finally:
        print()
        print()
        print()


def get_sku_procedure_id(ui_data_set, session_start_time, work_path, num):
    try:
        current_data = ui_data_set[num]
        print('Thread-{} 执行的数据集 -> {}'.format(num, str(current_data)))
        url = my_url + ":85/mira_server_api/client/production_status/" + str(current_data['station_id'])
        response = requests.request("GET", url, headers={'Content-Type': 'application/json',
                                                         'token': token})
        if response.status_code == 200:
            data = json.loads(response.text)
            print(data)
            if data['code'] == 200:
                procedure_id = data['data']['procedures'][0]['procedure_id']
                sku_switch_id = data['data']['sku_switch_id']
                if current_data['dynamic']:
                    write_dynamic_json(current_data, procedure_id, sku_switch_id, session_start_time, num, work_path)
                else:
                    write_static_json(current_data, procedure_id, sku_switch_id, session_start_time, num, work_path)
            else:
                print('Thread-{} 获取sku_procedure失败~'.format(num))
        else:
            print('Thread-{} 获取sku_procedure失败 / {}'.format(num, response.text))
    except Exception as e:
        traceback.print_exc()
        print('Thread-{} get sku_procedure失败 {}'.format(num, str(e)))


def write_dynamic_json(current_data, procedure_id, sku_switch_id, session_start_time, num, work_path):
    files = current_data['files']
    sno = 1
    for filename, value in files.items():
        save_file = []
        for i in range(value):
            index = filename.split('-')[1].replace('.json', '')
            if int(index) < 4:
                operation_time = random.randint(56, 65)
                attendant_time = random.randint(1, 10)
            else:
                operation_time = random.randint(66, 80)
                attendant_time = random.randint(21, 30)

            origin_file_path = './data/d/' + filename
            # output_name = filename.split('.')[0] + '_' + ymd + '_' + str(i) + '_T' + self.num + '.json'
            output_name = filename.split('.')[0] + '_' + str(i) + '_T' + str(num) + '.json'
            new_file_path = work_path + '/' + output_name
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
                file.write(new_json_data)

            session_start_time = session_end_time_str

        # 发送请求
        send_dynamic_request(current_data, num, save_file)


def write_static_json(current_data, procedure_id, sku_switch_id, session_start_time, num, work_path):
    static_files = current_data['static_files']
    sno = 1
    for filename, value in static_files.items():
        save_file = []
        for i in range(value):
            file_path = './data/s/' + filename
            new_file_path = work_path + '/' + filename.split('.')[0] + '_' + str(i) + '_T' + str(num) + '.json'
            save_file.append(new_file_path)

            # 读取原始JSON数据
            with open(file_path, 'r', encoding='utf8', errors='ignore') as file:
                json_data = file.read()

            # 解析JSON数据
            data = json.loads(json_data)

            data["StartTimeText"] = session_start_time
            data["SNNumebrText"] = str(sno).zfill(7)
            sno = sno + 1

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

        send_static_request(current_data, num, save_file, procedure_id, sku_switch_id)


def send_dynamic_request(currentData, num, save_file):
    for file_path in save_file:
        with open(file_path, 'r', encoding='utf8', errors='ignore') as f:
            json_content = json.load(f)
        try:
            url = my_url + ":85/mira_server_api/client/detect_result/dynamic/" + str(
                currentData['station_id'])
            response = requests.request("POST", json=json_content, url=url,
                                        headers={'Content-Type': 'application/json',
                                                 'token': token})
            data = json.loads(response.text)
            if response.status_code == 200:
                if data['code'] == 200:
                    print(' > Thread - {0}, 流水线 - {1} -> {2} 发送动态检测请求成功~ {3}'
                          .format(num, currentData['line_id'], os.path.basename(file_path), data['data']['message']))
                else:
                    print(' > Thread - {0}, 流水线 - {1} -> {2} 发送动态检测请求失败~ {3}'
                          .format(num, currentData['line_id'], os.path.basename(file_path), data['data']['message']))
            else:
                print(' > Thread - {0}, 流水线 - {1} -> {2} 发送动态检测请求失败'
                      .format(num, currentData['line_id'], os.path.basename(file_path)))
        except Exception as e:
            print(' > Thread - {0}, 流水线 - {1} -> {2} 发送动态检测请求失败~ {3}'
                  .format(num, currentData['line_id'], os.path.basename(file_path), str(e)))


def send_static_request(currentData, num, save_file, procedure_id, sku_switch_id):
    for file_path in save_file:
        with open(file_path, 'r', encoding='utf8', errors='ignore') as f:
            json_content = json.load(f)
            json_content = rebuild_json(json_content, procedure_id, sku_switch_id)
        try:
            url = my_url + ":85/mira_server_api/client/detect_result/static/" + \
                  str(currentData['station_id'])
            response = requests.request("POST", json=json_content, url=url,
                                        headers={'Content-Type': 'application/json',
                                                 'token': token})
            data = json.loads(response.text)
            if response.status_code == 200:
                if data['code'] == 200:
                    print(' > Thread - {0}, 流水线 - {1} -> {2} 发送静态检测请求成功~ {3}'
                          .format(num, currentData['line_id'], os.path.basename(file_path), data['data']['message']))
                else:
                    print(' > Thread - {0}, 流水线 - {1} -> {2} 发送静态检测请求失败~'
                          .format(num, currentData['line_id'], os.path.basename(file_path)))
            else:
                print(' > Thread - {0}, 流水线 - {1} -> {2} 发送静态检测请求失败'
                      .format(num, currentData['line_id'], os.path.basename(file_path)))
        except Exception as e:
            print(' > Thread - {0}, 流水线 - {1} -> {2} 发送静态检测请求失败~ {3}'
                  .format(num, currentData['line_id'], os.path.basename(file_path), str(e)))


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


def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)


def add_line(K):
    name = prefix + timestamp + "_line_" + str(K)
    try:
        url = my_url + ":85/mira_server_api/lines/add"
        payload = json.dumps({
            "name": name,
            "description": "",
            "copy_src_line_id": 0
        })
        response = requests.request("POST", data=payload, url=url, headers={'Content-Type': 'application/json',
                                                                            'token': token})
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print('{} 流水线创建成功 - {}'.format(name, response.text))
                return data['data']['line_id']
            else:
                print('{} 流水线创建失败!{}'.format(name, data['message']))
                return None
        else:
            print('{} 流水线创建失败 {}'.format(name, data['message']))
            return None
    except Exception as e:
        print('{} 流水线创建失败 {}'.format(name, str(e)))
        return None


def add_model(N):
    name = prefix + timestamp + "_model_" + str(N)
    try:
        url = my_url + ":85/mira_server_api/models"
        payload = json.dumps({
            "name": name,
            "pt_time": "99",
            "copy_src_model_id": -1,
            "sn_format": "^222.{33}[0-9]{1}.{222}ddd$",
            "description": "faker line_" + str(N),
            "machine_category_id": 1
        })
        response = requests.request("POST", data=payload, url=url, headers={'Content-Type': 'application/json',
                                                                            'token': token})
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print('{} 机型创建成功 - {}'.format(name, response.text))
                return data['data']['model_id']
            else:
                print('{} 机型创建失败!{}'.format(name, data['message']))
                return None
        else:
            print('{} 机型创建失败 {}'.format(name, data['message']))
            return None
    except Exception as e:
        print('{} 机型创建失败 {}'.format(name, str(e)))
        return None


def add_procedure(model_id, M):
    name = prefix + timestamp + "/" + str(model_id) + "_procedure_" + str(M)
    try:
        url = my_url + ":85/mira_server_api/models/" + str(model_id) + "/procedures"
        payload = json.dumps({
            "description": "",
            "name": name,
            "copy_src_procedure_id": 0,
            "step_missing_alertable": True,
            "step_disorder_alertable": True,
            "pt_overtime_alertable": True,
            "pt_overtime_stastics": True
        })
        response = requests.request("POST", data=payload, url=url, headers={'Content-Type': 'application/json',
                                                                            'token': token})
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print('{} 工序创建成功 - {}'.format(name, response.text))
                return data['data']['procedure_id']
            else:
                print('{} 工序创建失败!{}'.format(name, data['message']))
                return None
        else:
            print('{} 工序创建失败 {}'.format(name, response.text))
            return None
    except Exception as e:
        print('{} 工序创建失败 {}'.format(name, str(e)))
        return None


def line_bind_model(line_id, model_id):
    try:
        url = my_url + ":85/mira_server_api/lines/" + str(line_id) + "/models"
        payload = json.dumps({
            "models": [model_id]
        })
        response = requests.request("POST", data=payload, url=url, headers={'Content-Type': 'application/json',
                                                                            'token': token})
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print('流水线{}绑定机型{}成功 - {}'.format(line_id, model_id, response.text))
                return 0
            else:
                print('流水线{}绑定机型{}失败!{}'.format(line_id, model_id, data['message']))
                return -1
        else:
            print('流水线{}绑定机型{}失败 {} '.format(line_id, model_id, data['message']))
            return -1
    except Exception as e:
        print('流水线{}绑定机型{}失败 {}'.format(line_id, model_id, str(e)))
        return -1


def line_bind_station(line_id, M):
    name = prefix + timestamp + "_" + str(line_id) + "_station_" + str(M)
    try:
        url = my_url + ":85/mira_server_api/lines/" + str(line_id) + "/stations"
        payload = json.dumps({
                "stations": [{
                    "name": name,
                    "type": "0",
                    "description": "",
                    "copy_src_station_id": 0
                }]
        })
        response = requests.request("POST", data=payload, url=url, headers={'Content-Type': 'application/json',
                                                                            'token': token})
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print('流水线{}绑定工站{}成功 - {}'.format(line_id, name, response.text))
                return data['data']['station_ids'][0]
            else:
                print('流水线{}绑定工站{}失败!{}'.format(line_id, name, data['message']))
                return None
        else:
            print('流水线{}绑定工站{}失败 {}'.format(line_id, name, data['message']))
            return None
    except Exception as e:
        print('流水线{}绑定工站{}失败 {}'.format(line_id, name, str(e)))
        return None


def station_bind_procedures(station_id, procedure_id):
    try:
        url = my_url + ":85/mira_server_api/lines/stations/" + str(station_id) + "/associate_procedure"
        payload = json.dumps({
            "procedure_id": int(procedure_id)
        })
        response = requests.request("POST", data=payload, url=url, headers={'Content-Type': 'application/json',
                                                                            'token': token})
        data = json.loads(response.text)
        if response.status_code == 200:
            if data['code'] == 200:
                print('工站{}绑定工序{}成功 - {}'.format(station_id, procedure_id, response.text))
                return 0
            else:
                print('工站{}绑定工序{}失败!{}'.format(station_id, procedure_id, data['message']))
                return -1
        else:
            print('工站{}绑定工序{}失败 {}'.format(station_id, procedure_id, data['message']))
            return -1
    except Exception as e:
        print('工站{}绑定工序{}失败 {}'.format(station_id, procedure_id, str(e)))
        return -1


time_format = "%Y-%m-%d %H:%M:%S"
config = configparser.ConfigParser()
config.read('my.ini')
ip = config.get('conf', 'ip')
username = config.get('conf', 'username')
password = config.get('conf', 'password')
port = config.get('conf', 'port')
session_begin = config.get('conf', 'session_begin')
stop = config.get('conf', 'stop')
skip_view_list = config.get('conf', 'skip_view_list')
my_url = "http://" + ip

token = init_token()
prefix = ""
# timestamp = str(int(time.time()))
timestamp = "$"

