# from winreg import REG_RESOURCE_REQUIREMENTS_LIST

#This file for HardWare with Lift model : ZHB_X_V3.2 2017.07.18 FW: XZZE0_200908

import os
import serial
import redis
import time
import logging
from binascii import unhexlify, hexlify

# Access an environment variable
redis_host = os.environ.get("REDIS_HOST", "localhost")
com_port = os.environ.get("COMPORT", "/dev/ttyS0")

log_format = "%(asctime)s - %(levelname)s:%(message)s"
logging.basicConfig(level='WARNING', format=log_format)

global data_machine
global data_temperature


r = redis.Redis(host=redis_host, port=6379, db=0)
# r=redis.Redis(host='localhost', port=6379, db=0)
# r=redis.Redis(host='redis-14100.c302.asia-northeast1-1.gce.cloud.redislabs.com', port=14100, username='default', password='LiG3qZIU9Qjgx1n08XnjWmfmCq25x8WX', db=0)

baud_rate = 19200  # whatever baudrate you are listening to
# com_port1 = '/dev/serial0' #'COM12'  # replace with your first com port path
# com_port1 = '/dev/ttyS0'
com_port1 = com_port

# Read timeout to avoid waiting while there is no data on the buffer
ComRead_timeout = 0.5
# Write timeout to avoid waiting in case of write error on the serial port
ComWr_timeout = 0.01

# IPC_serial = serial.Serial(port=com_port1, baudrate=baud_rate, timeout=ComRead_timeout,
#                          write_timeout=ComWr_timeout, inter_byte_timeout = 0.1)

try:
    ser = serial.Serial(
        port=com_port1,
        baudrate=baud_rate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=ComRead_timeout
    )
    logging.critical("----OPEN---COM-PORT: %r", ser.isOpen())

    if not ser.isOpen():
        ser.open()
except Exception as e:
    logging.critical("Cannot open %r - %r" % (com_port1, str(e)))
    ser.flushInput()
    ser.flushOutput()
    ser.close()

cmd_data = ['74', '76', '78', '79', '7A', '7C', '7D', '7F', '85', '8B']
cmd_len = [22,   48,  110, 38,  40,  52,  44,  812, 18,  16]

counter_76 = 0
stage_machine = 0
order = ''

def write_file(data, mode):
    f = open("logging_transceive.txt", "a")
    f.write(time.time())
    if (mode):
        f.write("receive : ")
    else :
        f.write("send : ")
    f.write(data)
    f.write('\n')
    f.close() 

def data_receiver(ser, cmd_data, cmd_len):
    data_results = []
    logging.critical("In data receiver")
    data_string = ''
    data_machine_resp = ''
    buff = 0

    while 1:
        data_in = ser.inWaiting()

        if data_in == buff:
            pass
        else:
            # logging.critical("=================Data in len: %r", data_in)
            buff = data_in

        if data_in > 0:
            data_raw = hexlify(ser.read(data_in)).decode("utf-8").upper()
            # logging.critical("========Data in reader: %r", data_raw)
            if data_raw[:2] in cmd_data and len(data_raw) > 6 and data_raw[2:4] == '00':
                data_machine_resp = data_raw[:6]
                logging.critical(
                    "$$$$$$$$$$Data in data_machine_resp: %r", data_machine_resp)
                data_push = data_raw[:2] + '00' + data_raw[:2]
                logging.critical("Data Push: %r", data_push)
                ser.write(unhexlify(data_push))

                data_string = data_raw[6:]
                logging.critical("$$$$$$$$$$Data in result: %r", data_string)

                if len(data_raw) > 8:
                    data_push = data_string[:2] + '00' + data_string[:2]
                    logging.critical("Data Push: %r", data_push)
                    ser.write(unhexlify(data_push))
                ser.write(unhexlify('760076'))
            elif len(data_raw) > 2 and data_raw[2:4] != 'EF':
                data_string += data_raw

            elif data_raw[:2] in cmd_data:
                data_string = data_raw

            if data_raw == '760076':
                logging.critical("Data Force Push: %r", '760076')

            # logging.critical("=====!!!!===Data in data_string: %r", data_string)
            if data_string[:2] in cmd_data and data_string[2:4] == 'EF':
                index = cmd_data.index(data_string[:2])
                if len(data_string) >= cmd_len[index]:
                    # logging.critical("--------------Data in result: %r", data_string)
                    # logging.critical("--------------Data in data_machine_resp: %r", data_machine_resp)
                    if data_machine_resp != '':
                        data_results.append(data_machine_resp)
                    data_results.append(data_string)
                    break
            elif data_string[:2] in cmd_data and data_string[2:4] == '00':
                data_machine_resp = data_string
                data_results.append(data_machine_resp)
                data_machine_resp = ''

        time.sleep(0.01)
    logging.critical("!!!!!!!!!--Data in data_results: %r", data_results)
    write_file(data_results, 1)
    return data_results


def maintain(ser, cmd_data, cmd_len, stage_machine):
    counter_76 = 0

    while stage_machine < 2:
        data_results = data_receiver(ser, cmd_data, cmd_len)
        for msg_in in data_results:
            # logging.critical("MSG msg_recv: %r", msg_in)
            if len(msg_in) > 6:
                if msg_in[:2] == '76':
                    counter_76 += 1
                    # logging.critical("counter_76: %r", counter_76)
                if msg_in[:2] == '78' or msg_in[:2] == '85' or msg_in[:2] == '7E' or msg_in[:2] == '79' or (msg_in[:2] == '76' and counter_76 == 3):
                    data_push = msg_in[:2] + '00' + msg_in[:2]
                    logging.critical("Data Push: %r", data_push)
                    ser.write(unhexlify(data_push))
                    if msg_in[:2] == '76' and stage_machine == 1:
                        stage_machine = 2
                        break

                elif msg_in[:2] == '7A':
                    global data_machine
                    global data_temperature
                    data_machine = msg_in[30:32]
                    if data_machine == '01':
                        logging.critical("Single Machine: %r", data_machine)
                    elif data_machine == '02':
                        logging.critical("Dual Machine: %r", data_machine)
                    data_temperature = int(msg_in[32:34], 16)
                    logging.critical("Temperature: %r", data_temperature)
                    stage_machine = 1

                elif msg_in[:2] == '7D':
                    counter_76 = 0

    return stage_machine


def pre_sale(ser, cmd_data, cmd_len, stage_machine):
    logging.critical("In Pree Salee: ")
    while stage_machine == 2:
        ser.flushOutput()

        ser.write(unhexlify('760B0100000000000082'))
        logging.critical("--------------Data Push: %r", '760B0100000000000082')

        data_results = data_receiver(ser, cmd_data, cmd_len)
        # msg_sts, msg_recv = data_receiver(ser, cmd_data, cmd_len)
        for msg_in in data_results:
            logging.critical(
                "MSG presaleeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee: %r", msg_in)
            if len(msg_in) > 6:
                if msg_in == '76EFEEFE0000000000000000000000000000000000000051':
                    # logging.critical("Readyyyyyy Resp: %r", msg_in)

                    # data_push = '760B0100000000000082'
                    # logging.critical("--------------Data Push: %r", data_push)
                    # ser.write(unhexlify(data_push))
                    stage_machine = 3
                elif msg_in == '760076':
                    stage_machine = 2
                else:
                    stage_machine = 2

    return stage_machine


def after_sale(ser, cmd_data, cmd_len, stage_machine):
    logging.critical("In After Salee: ")
    if stage_machine == 4:
        data_results = data_receiver(ser, cmd_data, cmd_len)
        for msg_in in data_results:
            logging.critical("After sale MSGGGGGGGGG_Innnnnn: %r", msg_in)
            if len(msg_in) > 6:
                if msg_in[:2] == '7C':
                    ##### Lift Delivered ####
                    data_push = msg_in[:2] + '00' + msg_in[:2]
                    logging.critical("--------------Data Push: %r", data_push)
                    ##### Push 7C007C - Open the door ####
                    ser.write(unhexlify(data_push))

                    deliver_counter = time.time()
                    stage_machine = 5
                # elif:
                #     pass
    else:
        stage_machine = 3

    # stage_machine == 5 - Lift Delivered, Open the door ##
    lift_list = ['8BEFEEFE00000066', '8BEFEEFE00000167']
    """
    8BEFEEFE00000066 - Lift Available
    8BEFEEFE00000167 - Lift Sensor Detected
    """
    wait_remove_goods = 0
    deliver_left = 0
    while stage_machine == 5 and deliver_left < 180:
        data_results = data_receiver(ser, cmd_data, cmd_len)
        deliver_left = time.time()-deliver_counter
        for msg_in in data_results:
            logging.critical(
                "--------------Waiting Remove Goods Time: %r | Data: %r" % (deliver_left, data_results))
            if msg_in in lift_list:
                if msg_in == '8BEFEEFE00000066':
                    if deliver_left < 2:
                        logging.critical(
                            "-!!!!!!!!!!!!!!!!!!!!!!!-Slot Error-!!!!!!!!!!!!!!!!!!!!!!!!!-")
                        stage_machine = 7
                    elif deliver_left <= 101:
                        logging.critical(
                            "-!!!!!!!!!!!!!!!!!!!!!!!-Goods Delivered-!!!!!!!!!!!!!!!!!!!!!!!!!-")
                        # wait_remove_goods = 0
                        stage_machine = 6
                    elif deliver_left > 100:
                        logging.critical(
                            "-!!!!!!!!!!!!!!!!!!!!!!!-Deliver Timeout-!!!!!!!!!!!!!!!!!!!!!!!!!-")
                        stage_machine = 7
                elif msg_in == '8BEFEEFE00000167' and deliver_left < 180:
                    # wait_remove_goods += 1
                    stage_machine = 8

            elif msg_in[:2] == '7C' or msg_in[:2] == '79' or msg_in[:2] == '85':
                data_push = msg_in[:2] + '00' + msg_in[:2]
                logging.critical("--------------Data Push: %r", data_push)
                ser.write(unhexlify(data_push))
                # time.sleep(20)
            # elif wait_remove_goods > 0 and msg_in[:2] == '76':
            #     if wait_remove_goods < 3:
            #         data_push = '761600018D'
            #         logging.critical("--------------Data Push: %r", data_push)
            #         ser.write(unhexlify(data_push))
            #         logging.critical("--------------Trying Remove Goods: %r", wait_remove_goods)
            #         stage_machine = 5
            #     else:
            #         logging.critical("-!!!!!!!!!!!!!!!!!!!!!!!-Goods Stuck-!!!!!!!!!!!!!!!!!!!!!!!!!-")
            #         stage_machine = 22
            else:
                logging.critical(
                    "-!!!!!!!!!!!!!!!!!!!!!!!-Unknow Slot Command-!!!!!!!!!!!!!!!!!!!!!!!!!-")
                logging.critical("MSG msg_recv: %r", msg_in)
                if msg_in in lift_list:
                    if msg_in == '8BEFEEFE00000066':
                        stage_machine = 7
                    elif msg_in == '8BEFEEFE00000167':
                        stage_machine = 8
                else:
                    stage_machine = 10
                # stage_machine = 20

    # while stage_machine == 7:
    #     cmd_sta, cmd = get_command()
    #     data_results = data_receiver(ser, cmd_data, cmd_len)

    #     for msg_in in data_results:
    #         logging.critical("Stage_MC : %r :: MSG msg_recv: %r", stage_machine, msg_in)
    #         if msg_in[:2] == '7C' or msg_in[:2] == '79' or msg_in[:2] == '85' or msg_in[:2] == '7D' or msg_in[:2] == '7A':
    #             data_push = msg_in[:2] + '00' + msg_in[:2]
    #             # logging.critical("--------------Data Push: %r", data_push)
    #             ser.write(unhexlify(data_push))
    #         elif msg_in == '76EFEEFE0000000000000000000000000000000000000051':
    #             if cmd_sta == True and cmd == 'OPEN_GATE':
    #                 data_push = '761600018D'

    #             else:
    #                 data_push = msg_in[:2] + '00' + msg_in[:2]
    #             logging.critical("--------------Data Push: %r", data_push)
    #             ser.write(unhexlify(data_push))

    # while stage_machine == 8:
    #     data_results = data_receiver(ser, cmd_data, cmd_len)
    #     for msg_in in data_results:
    #         logging.critical("Stage_MC : %r :: MSG msg_recv: %r", stage_machine, msg_in)
    #         if msg_in[:2] == '76':
    #             if msg_in == '76EFEEFE0000000000000000000000000000000000000051':
    #                 data_push = '760b0200000000000083'
    #                 logging.critical("--------------Data Push: %r", data_push)
    #                 ser.write(unhexlify(data_push))
    #                 stage_machine = 21
    return stage_machine


def open_gate(ser, cmd_data, cmd_len, stage_machine):
    lift_list = ['8BEFEEFE00000066', '8BEFEEFE00000167']
    """
    8BEFEEFE00000066 - Lift Available
    8BEFEEFE00000167 - Lift Sensor Detected
    """
    # deliver_left = 0
    # deliver_counter = 0

    while stage_machine == 8:
        cmd_sta, cmd = get_command()
        data_results = data_receiver(ser, cmd_data, cmd_len)
        # deliver_left = time.time()-deliver_counter
        for msg_in in data_results:
            logging.critical(
                "Stage_MC : %r :: MSG msg_recv: %r", stage_machine, msg_in)
            if msg_in in lift_list:
                if msg_in == '8BEFEEFE00000066':
                    logging.critical(
                        "-!!!!!!!!!!!!!!!!!!!!!!!-Goods Delivered-!!!!!!!!!!!!!!!!!!!!!!!!!-")
                    logging.critical("<<------ Delivered ------->>")
                    put_response(order, 'S0')
                    stage_machine = 9
                elif msg_in == '8BEFEEFE00000167':
                    logging.critical(
                        "-!!!!!!!!!!!!!!!!!!!!!!!-Goods Stuck-!!!!!!!!!!!!!!!!!!!!!!!!!-")
                    logging.critical("<<------ product stuck ------->>")
                    put_response(order, 'E1')
            elif msg_in[:2] == '7C' or msg_in[:2] == '79' or msg_in[:2] == '85' or msg_in[:2] == '7D' or msg_in[:2] == '7A':
                data_push = msg_in[:2] + '00' + msg_in[:2]
                # logging.critical("--------------Data Push: %r", data_push)
                ser.write(unhexlify(data_push))
            elif msg_in == '76EFEEFE0000000000000000000000000000000000000051':
                if cmd_sta == True and cmd == 'OPEN_GATE':
                    data_push = '761600018D'
                    # deliver_counter = time.time()
                    logging.critical("--------------Data Push: %r", data_push)
                    ser.write(unhexlify(data_push))
                else:
                    data_push = msg_in[:2] + '00' + msg_in[:2]
                    logging.critical("--------------Data Push: %r", data_push)
                    ser.write(unhexlify(data_push))
    return stage_machine


def wait_reset_cmd(ser, cmd_data, cmd_len, stage_machine):
    while stage_machine == 7 or stage_machine == 10:
        cmd_sta, cmd = get_command()
        if cmd_sta == True and cmd == 'RESET':
            stage_machine = 11
        else:
            data_results = data_receiver(ser, cmd_data, cmd_len)
            for msg_in in data_results:
                data_push = msg_in[:2] + '00' + msg_in[:2]
                ser.write(unhexlify(data_push))

    return stage_machine


def slot_controller(slot_no):

    slot_row = slot_no // 10
    slot_col = slot_no % 10

    first_slot_msg = '7603000A'
    mid_slot_msg = '0000000000000000000000000000000000000000000000000000000001581'
    end_slot_row = ['5402758', '7234161', '732316A', '7364990', '74344A2']

    first_prepare = int(first_slot_msg, 16) + (slot_no-10)
    end_prepare = int(end_slot_row[slot_row-1], 16) + slot_col

    slot_full_msg = f'{first_prepare:x}' + mid_slot_msg + f'{end_prepare:x}'

    logging.critical("Slot No: %r | Msg Data: %r" %
                     (slot_no, slot_full_msg.upper()))
    logging.critical("Lennnnnnnnnn: %r | Msg Data: %r" %
                     (len(slot_full_msg.upper()), slot_full_msg.upper()))
    return slot_full_msg.upper()

# slot_no = 10

################################
##### Redis function       #####
################################


def get_queue():
    try:
        order = r.rpop('QUEUE').decode('UTF-8')
        if (order != None):
            return True, order
        else:
            return False, ''
    except Exception as e:
        logging.critical("Order Empty")
        return False, ''


def get_channel(order):
    # channel = order[6:9] #3 digit (010 :: cabinet : 0; channel : 10) , (110 :: cabinet : 1; channel : 10)
    # 3 digit (010 :: cabinet : 0; channel : 10) , (110 :: cabinet : 1; channel : 10)
    channel = order[7:9]
    return int(channel)


def get_command():
    try:
        cmd = r.rpop('COMMAND').decode('UTF-8')
        if (cmd != None):
            logging.critical("COMMAND: %r", cmd)
            return True, cmd
        else:
            return False, ''
    except Exception as e:
        logging.critical("Command Empty")
        return False, ''


def put_response(order, status):
    try:
        # status = 'S0', 'E0', 'E1'  :: ('S0' : success) , ('E0' : no product) , ('E1' : not pick product)
        return_val = order[0:9] + status
        item = r.lpush('RESPONSE', return_val)
        return True
    except Exception as e:
        logging.critical("redis error")
        return False


while 1:
    stage_machine = maintain(ser, cmd_data, cmd_len, stage_machine)
    logging.critical("Main Stageeeeeeeee: %r", stage_machine)

    get_q_sta, order = get_queue()
    if get_q_sta:
        slot_no = get_channel(order)
    ## stage_machine == 2 - pre-sale ##
        stage_machine = pre_sale(ser, cmd_data, cmd_len, stage_machine)

    ## stage_machine == 3 - ready to sell ##
    if stage_machine == 3:
        logging.critical("Readyyyy to selll: %r", stage_machine)

        # time.sleep(5)

        ser.write(unhexlify(slot_controller(slot_no)))
        # slot_no += 1

        stage_machine = 4

        stage_machine = after_sale(ser, cmd_data, cmd_len, stage_machine)

        # data_results = data_receiver(ser, cmd_data, cmd_len)
        # for msg_in in data_results:
        #     logging.critical("MSGGGGGGGGG_Innnnnn: %r", msg_in)
        #     if len(msg_in) > 6:
        #         data_push = msg_in[:2] + '00' + msg_in[:2]
        #         logging.critical("--------------Data Push: %r", data_push)
        #         ser.write(unhexlify(data_push))
        #         stage_machine = 7

        # data_results = data_receiver(ser, cmd_data, cmd_len)
        # for msg_in in data_results:
        #     logging.critical("MSGGGGGGGGG_Innnnnn: %r", msg_in)
        #     if len(msg_in) > 6:
        #         data_push = msg_in[:2] + '00' + msg_in[:2]
        #         logging.critical("--------------Data Push: %r", data_push)
        #         ser.write(unhexlify(data_push))
        #         stage_machine = 8
    if stage_machine == 6:
        logging.critical("<<------ Delivered ------->>")
        put_response(order, 'S0')

    if stage_machine == 7:
        logging.critical("<<------ Slot Error ------->>")
        put_response(order, 'E0')
        stage_machine = wait_reset_cmd(ser, cmd_data, cmd_len, stage_machine)

    if stage_machine == 8:
        logging.critical("<<------ product stuck ------->>")
        put_response(order, 'E1')
        stage_machine = open_gate(ser, cmd_data, cmd_len, stage_machine)

    if stage_machine == 10:
        logging.critical(
            "<<-------- Unknow Response from after sale process ------->>")
        put_response(order, 'E2')
        stage_machine = wait_reset_cmd(ser, cmd_data, cmd_len, stage_machine)

    if stage_machine == 11:
        logging.critical("<<---------- Reset Stage --------->>")

    stage_machine = 0
    order = ''
    # if slot_no == 60:
    #     while 1:
    #         time.sleep(10)
    time.sleep(2)
