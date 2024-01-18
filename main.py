import concurrent.futures
import time
from datetime import datetime, timedelta
import json
import api
import os

# def print_hello(date, thread_id):
#     thread_name = threading.current_thread().name
#     time.sleep(random.randint(0, 100))
#     print(f"Hello from {thread_id} - {thread_name}")


def mai_process(ui_data):
    folder_name = datetime.now().strftime("%Y%m%d%H%M%S")
    # 获取开始时间和结束时间
    start_day = datetime.strptime(ui_data["shift"]['shift_start_time'], "%Y-%m-%d")
    end_day = datetime.strptime(ui_data["shift"]['shift_end_time'], "%Y-%m-%d")
    start_hour = ui_data["shift"]['shift_start_hour']
    end_hour = ui_data["shift"]['shift_end_hour']

    works = len(ui_data['data_set'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=works) as executor:
        while start_day <= end_day:
            system_start_time = api.get_local_time(start_day, start_hour, end_hour)
            utc_time = api.get_utc_time(system_start_time)
            api.set_system_date(utc_time)

            # 开班
            shift_ng = False
            for element in view_list:
                result = api.force_start_shift_silent(element['line_id'], element['shift_id'],
                                                      element['model_id'])
                if result == -1:
                    shift_ng = True
                    print("流水线: {0},班次:{1},机型:{2}开班失败".format(element['line_id'], element['shift_id'], element['model_id']))
                    break

            if shift_ng:
                break

            work_path = './data/o/' + folder_name + '/' + start_day.strftime('%Y-%m-%d')
            os.makedirs(work_path, exist_ok=True)
            print('文件路径: ' + work_path + '\n')

            session_start_time = (datetime.strptime(system_start_time, api.time_format) +
                                  timedelta(seconds=int(api.session_begin))).strftime(api.time_format)

            futures = []
            for i in range(0, works):
                future = executor.submit(api.get_sku_procedure_id, ui_data['data_set'], session_start_time, work_path, i)
                futures.append(future)

            # 等待当前一组线程执行完成
            for future in concurrent.futures.as_completed(futures):
                time.sleep(5)
                future.result()
            # 开始停班
            print('start stop ...')
            if api.stop != 0:
                time.sleep(int(api.stop))
            for lines in view_list:
                api.stop_shift_silent(lines['line_id'])

            start_day += timedelta(days=1)


if __name__ == '__main__':
    with open('u1.json', 'r') as file:
        ui_data_set = json.load(file)
    with open('v1.json', 'r') as file:
        view_list = json.load(file)

    print(ui_data_set)
    print(view_list)

    mai_process(ui_data_set)
