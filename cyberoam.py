import base64
import ctypes
import json
import logging
import os
import subprocess
import sys
import threading
import urllib.request
from random import randint
from time import perf_counter, sleep

from cryptography.fernet import Fernet
from PyQt5.QtCore import QThread, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from selenium.webdriver import PhantomJS
from selenium.webdriver.support.wait import WebDriverWait


def write_hidden(data):

    HIDDEN = 0x02
    file_name = "data.json"

    prefix = "." if os.name != "nt" else ""
    file_name = prefix + file_name
    try:
        with open(file_name, "w") as f:
            json.dump(data, f)
    except Exception:
        os.remove(file_name)
        with open(file_name, "w") as f:
            json.dump(data, f)
    if os.name == "nt":
        ret = ctypes.windll.kernel32.SetFileAttributesW(file_name, HIDDEN)
        if not ret:
            raise ctypes.WinError()


class CyberThread(QThread):
    fsignal = pyqtSignal(str)
    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.loop = True
        self.pause = False # pause loop
        with open("cyberoam.log", "w"):
            pass
        self.logger = logging.getLogger("cyberoam")
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler("cyberoam.log")
        # c_handler.setLevel(logging.WARNING)
        # f_handler.setLevel(logging.WARNING)

        c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        f_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        self.logger.addHandler(c_handler)
        self.logger.addHandler(f_handler)
        self.driver = None
        self.login = None
        self.logger.warning("############### NEW SESSION ###############")


    def run(self):

        while self.loop:
            while not self.pause:
                try:
                    with open("data.json", "r") as self.fobj:
                        data = json.load(self.fobj)
                        key = data["Build_data"]
                        fnet = Fernet(key)
                        self.studid = fnet.decrypt(data.get("STUDENTID").encode()).decode()
                        self.passwd = fnet.decrypt(data.get("PASSKEY").encode()).decode()
                        self.pause = True
                except Exception:
                    self.fsignal.emit("give credentials")
                    sleep(1)
            try:
                self.driver = PhantomJS(r"./bin/phantomjs.exe")
                wait = WebDriverWait(self.driver, timeout=10)
                if not self.login_cyberoam():
                    continue
                i = 0
                while self.internet_on() and self.loop:
                    self.logger.warning(
                        "def connect_cyberoam: while internet_on(): internet working for {} units.".format(
                            i
                        )
                    )
                    i += 1
                    if i > 210:
                        if not self.login_cyberoam():
                            continue
                        i = 0
                    sleep(30)
                self.logger.warning(
                    "def connect_cyberoam: while run: closing driver cause internet not working."
                )
                self.login.click()
                self.driver.quit()
                self.driver = None
                continue
            except Exception as e:
                self.logger.exception(
                    "def connect_cyberoam: while run: except: {}".format(e)
                )

            finally:
                self.logger.warning(
                    "def connect_cyberoam: finally: terminating driver session"
                )
                try:
                    if self.driver is not None:
                        if self.login is not None:
                            self.login.click()
                        self.driver.quit()
                    sleep(10)
                except Exception as e:
                    self.logger.exception(e)
                self.logger.warning("end: driver session terminated successfully")

    def internet_on(self):
        try:
            urllib.request.urlopen("http://172.217.163.78", timeout=1)  # google.com
            return True
        except Exception:
            try:
                urllib.request.urlopen(
                    "http://172.217.166.174", timeout=1
                )  # google.com
                return True
            except Exception:
                try:
                    urllib.request.urlopen("http://google.com", timeout=2)
                    return True
                except Exception:
                    try:
                        urllib.request.urlopen("http://wikipedia.org", timeout=2)
                        return True
                    except Exception:
                        return False

    def login_cyberoam(self):
        d = ("०१२३४५६७८९", "૦૧૨૩૪૫૬૭૮૯", "0123456789")
        self.driver.get("http://cyberoam.daiict.ac.in:8090")

        usern = self.driver.find_element_by_name("username")
        passw = self.driver.find_element_by_name("password")
        lis = [randint(0, 2) for i in range(9)]
        usr = ""
        for i in range(9):
            usr += d[lis[i]][int(self.studid[i])]
        usern.send_keys(usr)
        passw.send_keys(self.passwd)
        self.login = self.driver.find_element(by="id", value="loginbutton")
        self.login.click()
        status = self.driver.find_element(by="id", value="statusmessage")
        status = status.get_attribute("innerHTML")
        if status == "Login failed. You have reached the maximum login limit.":
            self.logger.warning(
                "def login_cyberoam: Login failed. You have reached the maximum login limit."
            )
            self.driver.quit()
            return False
        else:
            sleep(1)
            status = self.driver.find_element(by="id", value="signin-caption")
            status = status.get_attribute("innerHTML")
            self.logger.warning("def login_cyberoam: successfully login to cyberoam.")
            return True



class SetPass(QDialog):
    def __init__(self):
        super().__init__()
        self.title = "set user credentials"
        self.left = 10
        self.top = 45
        self.width = 320
        self.height = 100
        self.submitButton = QPushButton("submit")
        self.submitButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submitButton.clicked.connect(self.handleSubmit)
        self.UserName = QLineEdit(self)
        self.Password = QLineEdit(self)
        self.Password.setEchoMode(QLineEdit.Password)
        self.initUI()

    def handleSubmit(self):
        key = Fernet.generate_key()
        f = Fernet(key)
        d = {}
        d["Build_data"] = key.decode()
        d["STUDENTID"] = f.encrypt(self.UserName.text().encode()).decode()
        d["PASSKEY"] = f.encrypt(self.Password.text().encode()).decode()
        write_hidden(d)
        self.hide()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.createGridLayout()

        windowLayout = QVBoxLayout()
        windowLayout.addWidget(self.horizontalGroupBox)
        windowLayout.addWidget(self.submitButton)
        self.setLayout(windowLayout)

    def createGridLayout(self):
        self.horizontalGroupBox = QGroupBox("Grid")
        layout = QGridLayout()

        layout.addWidget(QLabel("Username"), 0, 0)
        layout.addWidget(self.UserName, 0, 1)

        layout.addWidget(QLabel("Password"), 1, 0)
        layout.addWidget(self.Password, 1, 1)

        self.horizontalGroupBox.setLayout(layout)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        
        self.studid = ""
        self.passwd = ""
        menu = QMenu(parent)
        exitAction = menu.addAction("Exit")
        credential = menu.addAction("Credentials")
        exitAction.triggered.connect(self.exitapp)
        self.set_pass_dialog = SetPass()
        credential.triggered.connect(self.set_pass_dialog.show)
        self.setContextMenu(menu)
        self.main_thread = CyberThread()
        self.main_thread.fsignal.connect(self.set_pass_dialog.show)
        self.main_thread.start()

    def exitapp(self):
        self.main_thread.loop = False
        self.main_thread.wait()
        sys.exit()


def main():
    app = QApplication(sys.argv)

    w = QWidget()
    trayIcon = SystemTrayIcon(QIcon("internet.ico"), w)

    trayIcon.show()
        

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
