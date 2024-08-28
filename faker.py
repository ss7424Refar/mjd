import argparse
import time

import api as api

if __name__ == '__main__':

    start_time = time.time()

    # 流水线(K) 机型（N）, 工序/工站 M
    parser = argparse.ArgumentParser(description='K')
    parser.add_argument('--K', type=int, help='Line')
    parser.add_argument('--M', type=int, help='Procedures/Station')
    parser.add_argument('--N', type=int, help='Model')
    parser.add_argument('--prefix', type=str, help='Prefix')
    args = parser.parse_args()

    api.prefix = args.prefix
    # 生成K条流线
    line_ids = []
    for k in range(0, args.K):
        line_id = api.add_line(k)
        line_ids.append(line_id)

    # print(line_ids)

    # 创建机型
    model_ids = []
    for n in range(0, args.N):
        model_id = api.add_model(n)
        model_ids.append(model_id)

    # print(model_ids)

    # 创建工序
    model_procedures_ids = {}
    for i in range(0, len(model_ids)):
        model_procedures_ids[model_ids[i]] = []
        for j in range(0, args.M):
            procedures_id = api.add_procedure(model_ids[i], j)
            model_procedures_ids[model_ids[i]].append(procedures_id)

    # print(model_procedures_ids)

    # 流水线绑定机型
    for i in range(0, len(line_ids)):
        for j in range(0, len(model_ids)):
            api.line_bind_model(line_ids[i], model_ids[j])

    # 流水线添加工站
    line_station_ids = {}
    for i in range(0, len(line_ids)):
        line_station_ids[line_ids[i]] = []
        for j in range(0, args.M):
            station_id = api.line_bind_station(line_ids[i], j)
            line_station_ids[line_ids[i]].append(station_id)

    # print(line_station_ids)
    # 选择机型后, 工站和工序一一对应
    for k in range(0, args.K):
        for n in range(0, args.N):
            for m in range(0, args.M):
                # print(line_station_ids[line_ids[k]][m], model_procedures_ids[model_ids[n]][m])
                api.station_bind_procedures(line_station_ids[line_ids[k]][m], model_procedures_ids[model_ids[n]][m])

    current_time = time.time() - start_time

    m, s = divmod(current_time, 60)
    h, m = divmod(m, 60)
    runtime_str = "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))
    print()
    print('Time taken to complete -> {}'.format(runtime_str))
