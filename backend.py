import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5 import QtGui
from PyQt5.QtGui import QPixmap
from main_ui import Ui_MainWindow
import requests
import serial
from spinner import WaitingSpinner
import time
from header import *
import pysher
import sys
import logging
import json
from datetime import datetime, timedelta
import hashlib

global password
global response


global lock_password_dict
lock_password_dict = ""

global recent_open_time_dict
recent_open_time_dict = ""
def get_current_time():
    try:
        response = requests.get('http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh')
        if response.status_code == 200:
            data = response.json()
            current_time = data['datetime']
            return current_time
        else:
            print("Failed to retrieve time from the internet.")
            return None
    except Exception as e:
        print("An error occurred:", e)
        return None

def generate_hash(input_string):

    hash_object = hashlib.sha256()

    hash_object.update(input_string.encode())

    return hash_object.hexdigest()


class checkOpenLocker(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(checkOpenLocker, self).__init__(parent)

    def run(self):
        api_interval = 6000 # Thời gian giữa các lần gửi API (đơn vị: giây)
        last_api_time = time.time()
        while True:
            current_time = time.time()

            if current_time - last_api_time >= api_interval:
                print("Check locker:")
                print("TIME DICT: ",recent_open_time_dict)
                serial_port = serial.Serial('/dev/ttyS0', 9600, timeout=3)
                lockerNumberStr = '100'
                serial_port.write(lockerNumberStr.encode())
                
                print("Run receive_uart")
                received_data = serial_port.read(256)
                print("Received data:", received_data)
                if recent_open_time_dict != '':
                    for id,open_time in recent_open_time_dict.items():
                        for locker in received_data[:-1]:
                            if id == locker:
                                current_time_open = get_current_time()
                                time_to_subtract = open_time
                                current_time_dt = datetime.fromisoformat(current_time_open)
                                time_to_subtract_dt = datetime.fromisoformat(time_to_subtract)
                                
                                time_difference = current_time_dt - time_to_subtract_dt

                                # Khoảng thời gian mong muốn (5 phút)
                                desired_difference = timedelta(seconds=120)

                                # So sánh kết quả với khoảng thời gian mong muốn
                                if time_difference >= desired_difference:
                                    print("Chênh lệch thời gian là 5 phút hoặc nhiều hơn.")
                                else:
                                    print("Chênh lệch thời gian là dưới 5 phút.")             
                last_api_time = current_time
                serial_port.close()
                
            time.sleep(1)
                

class SendAPI(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(SendAPI, self).__init__(parent)

    def run(self):
        api_interval = 5  # Thời gian giữa các lần gửi API (đơn vị: giây)
        last_api_time = time.time()

        while True:
            current_time = time.time()

            if current_time - last_api_time >= api_interval:
                #Get Sync API
                
                global lock_password_dict
                try:
                        sync_response = requests.get(sync_url, headers=api_headers)
                except:
                    print("Send API Error")
                sync_response.raise_for_status()
                # data = sync_response.json().get("data", [])
                # lock_password_dict = {item.get("pin_code", ""): item.get("row", "") for item in data}
                # print(str(lock_password_dict))
                # #Get Log-active API               
                # log_response = requests.get(log_active_url, headers=api_headers)
                # log_response.raise_for_status()
                # print(log_response.text)
                
                    
                last_api_time = current_time

            # Thêm một khoảng thời gian ngủ nhỏ để giảm tải CPU
            time.sleep(1)


class WorkerThread(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, parent=None):
        super(WorkerThread, self).__init__(parent)

    def run(self):
        main_win.on_submit_clicked()
        self.finished_signal.emit()


class MainWindow(QMainWindow):
    TIMEOUT_LIMIT = 128
    TIMEOUT_INTERVAL = 10

    def __init__(self):
        super().__init__()
        self.uic = Ui_MainWindow()
        self.uic.setupUi(self)
        self.uic.textEdit.setWordWrapMode(QtGui.QTextOption.NoWrap)

        self.spinner_container = QWidget(self)
        self.spinner_container.setGeometry(260, 320, 80, 80)

        self.waiting_spinner = WaitingSpinner(self.spinner_container)
        self.waiting_spinner.setGeometry(0, 0, 80, 80)

        # Hide some objects
        self.uic.waiting_msg.hide()
        self.uic.confirm_popup.hide()
        self.uic.wrong_pass_label.hide()
        self.uic.admin_popup.hide()
        self.uic.btOpenAll.hide()

        self.worker_thread = WorkerThread()
        self.worker_thread.finished_signal.connect(self.stop_spinner)

        # self.serial_port = serial.Serial('/dev/ttyS0', 9600)
        self.api_timeout = 10
        self.mode = USER_MODE
        self.addmin_pass = "000000"
        self.count = 0
        self.current_use_pass = ''
        
        
        self.root = logging.getLogger()
        self.root.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        self.root.addHandler(ch)
        self.pusher = pysher.Pusher('4d00bbd9faf873abcbaf',cluster="ap1")
        self.pusher.connection.bind('pusher:connection_established', self.connect_handler)
        self.pusher.connect()

        for i in range(0, 10):
            getattr(self.uic, f"bt{i}").clicked.connect(
                lambda _, i=str(i): self.on_button_clicked(i))

        self.uic.bt_code.clicked.connect(self.enter_code_ui)
        self.uic.bt_qr.clicked.connect(self.scan_qr_ui)
        self.uic.stackedWidget.setCurrentIndex(0)

        self.uic.bt_back_scan_qr.clicked.connect(self.back_to_main_ui)
        self.uic.bt_back_enter_code.clicked.connect(self.back_to_main_ui)

        self.uic.btSao.clicked.connect(self.on_sao_clicked)
        self.uic.btDel.clicked.connect(self.on_delete_clicked)
        self.uic.btSubmit.clicked.connect(self.on_submit_clicked3)
        self.uic.btConfirm.clicked.connect(self.uic.confirm_popup.hide)
        self.uic.btGotIt.clicked.connect(self.on_gotit_clicked)
        self.uic.btOpenAll.clicked.connect(self.on_open_all_clicked)

        self.send_sync_api_thread = SendAPI()
        self.send_sync_api_thread.start()
        
        self.check_locker_thread = checkOpenLocker()
        self.check_locker_thread.start()
        self.uic.btOpenLock.clicked.connect(self.on_btOpenLock_clicked)
        
        self.uic.btOpenLock.hide()
        
        #------ RUN AD IMAGE ------#
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.change_image)
        self.timer.start(3000)  
        self.image_paths = [
    "./image/pic_1.png", 
    "./image/pic_2.png", 
    "./image/pic_3.png"
    ]

        self.current_image_index = 0
        self.change_image()
    def change_image(self):

        image_path = self.image_paths[self.current_image_index]
        image_path = self.image_paths[self.current_image_index]

        # Hiển thị ảnh trong label
        pixmap = QPixmap(image_path)
        self.uic.ad_label.setPixmap(pixmap)

        # Tăng chỉ số của ảnh hoặc quay lại ảnh đầu tiên nếu đã đến ảnh cuối cùng
        self.current_image_index += 1
        if self.current_image_index >= len(self.image_paths):
            self.current_image_index = 0
            
            
            
        #-----------Pusher Function-------------
    def my_func(self, *args, **kwargs):
        print("processing Args:", args)
        print("processing Kwargs:", kwargs)
        if args:
            try:
                data = json.loads(args[0])
                content = json.loads(data["notification"]["content"])
                print("Content:", content)
                lockerNumber = content['slot_number']
                print("Type: ", type(lockerNumber))
                # mySerialPort = self.start_uart()
                # self.send_uart(lockerNumber, mySerialPort)
                self.exec_uart(lockerNumber)
                
            except Exception as e:
                print("Error:", e)
        
    def connect_handler(self, data):
        channel = self.pusher.subscribe('notification.lockerSystem.1.1')
        channel.bind('App\\Events\\NotificationProcessed', self.my_func)

    
    def on_btOpenLock_clicked(self):
        lockerNumber = self.uic.textEdit.toPlainText()
        if len(lockerNumber) >= 1:
            print(f"Locker Input: {lockerNumber}")
            mySerialPort = self.start_uart()
            self.send_uart(lockerNumber, mySerialPort)
            mySerialPort.close
        
    def get_offline_password(self):
        global lock_password_dict
        if lock_password_dict != "":
            print("Dict: ", str(lock_password_dict))
            password = self.uic.textEdit.toPlainText()
            for pin_code, row  in lock_password_dict.items():
                print(f"Pin code: {pin_code}, Pass word: {password}")
                if pin_code == password:
                    return int(row)
        return None

    def clear_password(self):
        self.uic.textEdit.setPlainText("")

    def start_uart(self):
        mySerial = serial.Serial('/dev/ttyS0', 9600, timeout=3)
        return mySerial

    def close_uart(self, mySerial):
        mySerial.close()

    def start_spinner(self):
        self.uic.waiting_msg.show()
        self.waiting_spinner.start()

    def stop_spinner(self):
        self.uic.waiting_msg.hide()
        self.waiting_spinner.stop()
        self.uic.textEdit.clear()

    def on_gotit_clicked(self):
        self.uic.admin_popup.close()
        self.uic.btOpenLock.move(350,410)
        self.uic.btOpenLock.show()
        self.uic.btSubmit.hide()
        self.clear_password()
        self.uic.btOpenAll.show()
        
    def show_admin_mode(self):
        self.uic.admin_popup.move(50,210)
        self.uic.admin_popup.show() 
        print("SHOW")
    def show_user_mode(self):
        self.uic.admin_popup.hide()
        self.uic.btOpenLock.hide()
        # self.uic.btSubmit.move(170,410)
        self.uic.btSubmit.show()
        self.clear_password()
        self.uic.btOpenAll.hide()
        print("SHOW")
        
    def on_open_all_clicked(self):
        serial_port = self.start_uart()
        code  = 999
        serial_port.write(str(code).encode())
        serial_port.close()
        

    def on_submit_clicked3(self):
        # self.count = 0
        password = self.uic.textEdit.toPlainText()
        print("Count: ", self.count)
        if self.mode == USER_MODE and self.count != 5:
            if password is not None and len(password) == 6:
                print("Start Spinner")
                self.start_spinner()
                self.worker_thread.start()
        elif self.count == 5:
            self.count = 0
            self.mode = ADMIN_MODE
            print("Enter Admin Mode")
            print(password)
            if password == self.addmin_pass:
                print("ADMIN MODE")
                self.show_admin_mode()
        # elif self.mode == ADMIN_MODE:
        #     print(password)
        #     if password == self.addmin_pass:
        #         print("ADMIN MODE")
        #         self.show_admin_mode()

    def enter_code_ui(self):
        self.uic.stackedWidget.setCurrentIndex(1)   

    def scan_qr_ui(self):
        self.uic.stackedWidget.setCurrentIndex(2)

    def back_to_main_ui(self):
        self.mode = USER_MODE
        self.show_user_mode()
        self.uic.stackedWidget.setCurrentIndex(0)

    def on_delete_clicked(self):
        self.waiting_spinner.stop()
        current_text = self.uic.textEdit.toPlainText()

        if current_text:
            new_text = current_text[:-1]
            self.uic.textEdit.setPlainText(new_text)

    def on_button_clicked(self, digit):
        self.uic.wrong_pass_label.hide()
        current_text = self.uic.textEdit.toPlainText()
        if self.mode == USER_MODE:
            if len(current_text) < 6:
                self.uic.textEdit.setPlainText(current_text + str(digit))
        elif self.mode == ADMIN_MODE:
            if len(current_text) < 2:
                self.uic.textEdit.setPlainText(current_text + str(digit))
        
    def on_sao_clicked(self):
        self.uic.wrong_pass_label.hide()
        # self.count = self.count + 1
        if self.count > 5:
            self.count = 0
        self.count = self.count + 1
        #     print("ADMIN_MODE A")
        #     self.mode = ADMIN_MODE
        # else:
        #     self.mode = USER_MODE
            
    def reset_password(self):
        
        body = {"password": self.current_use_pass}
        response = requests.post(
                reset_pass_url, headers=api_headers, json=body)
        print("API RESET PASS: ", response.text)
    def check_API_response(self):
        password = self.uic.textEdit.toPlainText()

        if not password:
            return API_ERROR

        body = {"password": password}
        print(password)
        self.current_use_pass = password
        try:
            global response
            response = requests.post(
                unlock_url, headers=api_headers, json=body)
            print("API: ", response.text)
            self.reset_password()
            return API_OK if response.status_code == 200 else API_ERROR
        except:
            return API_ERROR

    def check_password(self):
        global response

        response_data = response.json()
        status = response_data.get("status", "")

        return PASSWORD_CORRECT if status == 'success' else PASSWORD_INCORRECT

    def add_zero_and_to_str(self, lockerNumberInt):
        if lockerNumberInt > 100:
            lockerNumberStr = str(lockerNumberInt)
        elif lockerNumberInt > 10:
            lockerNumberStr = '0' + str(lockerNumberInt)
        else:
            lockerNumberStr = '00' + str(lockerNumberInt)
        return lockerNumberStr

    def get_loker_number(self):
        global response
        response_data = response.json()
        print(response_data)

        lockerNumberInt = response_data.get("data").get("numOfLocker", "")
        print("numofLocker: ", lockerNumberInt)
        return lockerNumberInt-1

    def show_confirm_popup(self, lockerNumberInt):
        global response
        self.uic.confirm_popup.move(50, 210)
        # lockerNumberInt = self.get_loker_number()
        print("LOCKER: ", lockerNumberInt)
        if lockerNumberInt is not None:
            lockerNumberInt = lockerNumberInt + 1
            self.uic.confirm_msg.setText(
                f"LOCKER NUMBER {lockerNumberInt} HAS BEEN OPENED \n"
                "NOTE: PLEASE CLOSE THE LOCKER DOOR CAREFULLY AFTER COMPLETING SENDING/RECEIVING ITEMS \n"
                "THANK YOU")
            self.uic.confirm_popup.show()
    def show_wrong_pass_popup(self):
        self.uic.wrong_pass_label.move(30,310)
        self.uic.wrong_pass_label.show()

    def send_uart(self, lockerNumber, serial_port):
        # print("Send Uart")
        if isinstance(lockerNumber, int):
            print("Number INT")
            lockerNumberStr = self.add_zero_and_to_str(lockerNumber)
            print("Locker Number IntStr:", lockerNumberStr)
            serial_port.write(lockerNumberStr.encode())
        else:
            print("Number STR")
            lockerNumberInt = int(lockerNumber) - 1
            lockerNumberStr = self.add_zero_and_to_str(lockerNumberInt)
            print("Locker Number Str:", lockerNumberStr)
            serial_port.write(lockerNumberStr.encode())
            # print("Đã send")

    def notify_open_lock(self, lockerNumber):
        print("Notify to the Web with Opening Locker: ", lockerNumber)

    def receive_uart(self, serial_port, lockerNumberInt):
        serial_port = self.start_uart()
        print("Run receive_uart")
        received_data = serial_port.read(256)
        print("Received data:", received_data)
        # lockerNumberInt = self.get_loker_number()
        if len(received_data) <= 1:
            return UNLOCK_ERROR
        elif len(received_data) == 2 and (len(received_data) - 1) == 70:
            if received_data[0] == lockerNumberInt:
                return UNLOCK_OK
            else:
                self.notify_open_lock(received_data[0])
                return UNLOCK_ERROR
        else:
            if received_data[len(received_data) - 1] == 70:
                unlock_flag = 0
                i = 0
                for i in range(len(received_data)-1):
                    if received_data[i] == lockerNumberInt:
                        unlock_flag = 1
                    else:
                        self.notify_open_lock(received_data[i])
                if unlock_flag == 1:
                    return UNLOCK_OK
                else:
                    return UNLOCK_ERROR
    def get_current_time(self):
        try:
            response = requests.get('http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh')
            if response.status_code == 200:
                data = response.json()
                current_time = data['datetime']
                return current_time
            else:
                print("Failed to retrieve time from the internet.")
                return None
        except Exception as e:
            print("An error occurred:", e)
            return None
    def exec_uart(self, lockerNumberInt):
        mySerialPort = self.start_uart()
        start_time = time.time()
        while(1):
            self.send_uart(lockerNumberInt, mySerialPort)

            unlockStatus = self.receive_uart(mySerialPort, lockerNumberInt)

            if unlockStatus == UNLOCK_OK:
                global recent_open_time_dict
                time_opem =  self.get_current_time()
                recent_open_time_dict = {lockerNumberInt : time_opem}
                print("TIME DICT: ",recent_open_time_dict)
                self.show_confirm_popup(lockerNumberInt)
                self.close_uart(mySerialPort)
                break

            if time.time() - start_time >= 30:
                print("Timeout! Exiting the on_submit_clicked")
                break
        
    
    def on_submit_clicked(self):
        
        # lockerNumberInt = 0
        # self.exec_uart(lockerNumberInt)
        
        print("Run on_submit_clicked")
        if self.check_API_response() == API_OK:
            print("Check API OK")
            if self.check_password() == PASSWORD_CORRECT:
                print("Check password OK")
                lockerNumberInt = self.get_loker_number()
                # lockerNumberInt = 1
                self.exec_uart(lockerNumberInt)
            else:
                print("Wrong Password")
                self.show_wrong_pass_popup()
                return
        else:
            lockerNumberInt = self.get_offline_password()
            if lockerNumberInt is not None:
                self.exec_uart(lockerNumberInt)
            else:
                
                print("Wrong Password Offline")
                self.show_wrong_pass_popup()
                return

    def closeEvent(self, event):
        self.send_sync_api_thread.quit()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.showFullScreen()
    sys.exit(app.exec_())
