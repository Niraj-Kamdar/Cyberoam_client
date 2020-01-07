import base64
import ctypes
import json
import logging
import os
import re
import subprocess
import sys
import urllib.parse as up
import urllib.request as ur
from random import randint
from time import perf_counter, sleep, time
from xml.dom.minidom import parseString

from cryptography.fernet import Fernet
from PyQt5.QtCore import QCoreApplication, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QDialog, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMenu,
                             QPushButton, QSizePolicy, QSystemTrayIcon,
                             QVBoxLayout, QWidget)


def write_hidden(data, file_name):

    HIDDEN = 0x02

    prefix = "." if os.name != "nt" else ""
    file_name = prefix + file_name
    with open(file_name, "w") as f:
        if data:
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
        try:
            with open("cyberoam.log", "r"):
                pass
            with open("cyberoam.log", "w"):
                pass
        except FileNotFoundError:
            write_hidden(None, "cyberoam.log")
            
        self.logger = logging.getLogger("cyberoam")
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler("cyberoam.log")

        c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        f_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        self.logger.addHandler(c_handler)
        self.logger.addHandler(f_handler)
        self.logger.warning("############### NEW SESSION ###############")


    def run(self):

        while self.loop:
            while not self.pause:
                try:
                    with open("data.json", "r") as self.fobj:
                        data = json.load(self.fobj)
                        key = data.get("Build_data")
                        fnet = Fernet(key)
                        self.studid = fnet.decrypt(data.get("STUDENTID").encode()).decode()
                        self.passwd = fnet.decrypt(data.get("PASSKEY").encode()).decode()
                        self.url = data.get("url")
                        self.pause = True
                        self.login()
                except FileNotFoundError:
                    self.fsignal.emit("give credentials")
                    sleep(1)
            self.relogin()
            sleep(5)
        self.logout()

    def relogin(self):
        data = {"mode":"192",
                "username":self.studid,
                "a":(str)((int)(time() * 1000))}
        try:
            self.logger.warning("Sending ack request...")
            myfile = ur.urlopen(self.url + "live?" + up.urlencode(data), timeout=3)
            data = myfile.read()
            myfile.close()
            dom = parseString(data)
            xmlTag = dom.getElementsByTagName('ack')[0].toxml()
            message = re.search("\[[A-Z a-z{}.]*\]", xmlTag).group(0)
            if 'ack' in message:
                self.logger.warning("You are logged in")
            else:
                self.logger.error("Error: Server response not recognized: " + message)
                self.logout()
                self.login()
        except Exception as e:
            self.logger.error("Error: {}".format(e))
            self.logout()
            self.login()
            return

                
    def logout(self):
        data = {"mode":"193",
                "username":self.studid,
                "a":(str)((int)(time() * 1000))}

        try:
            self.logger.warning("Sending logout request...")
            myfile = ur.urlopen(self.url + "logout.xml", up.urlencode(data).encode("utf-8"), timeout=3)
            data = myfile.read()
            myfile.close()
            dom = parseString(data)
            xmlTag = dom.getElementsByTagName('message')[0].toxml()
            message = re.search("\[[A-Z a-z{}.]*\]", xmlTag).group(0)
            self.logger.warning(message)
        except Exception as e:
            self.logger.error("Error: {}".format(e))


    def login(self):
        d = ("०१२३४५६७८९", "૦૧૨૩૪૫૬૭૮૯", "0123456789")
        user = self.studid
        self.studid = ''.join(map(lambda x: d[randint(0, 2)][int(x)], self.studid))
        data =  {   "mode":"191",
                    "username": self.studid,
                    "password":self.passwd,
                    "a":(str)((int)(time() * 1000))}
        try:
            myfile = ur.urlopen(self.url + "login.xml", 
                                up.urlencode(data).encode("utf-8"),
                                timeout=3)
            data = myfile.read()
            myfile.close()
            dom = parseString(data)
            xmlTag = dom.getElementsByTagName('message')[0].toxml()
            message = re.search("\[[A-Z a-z{}.]*\]", xmlTag).group(0)
            xmlTag = dom.getElementsByTagName('status')[0].toxml()
            status = re.search("\[[A-Z a-z{}.]*\]", xmlTag).group(0)
            if 'live' in status.lower():
                self.logger.warning(
                    "Login: {}".format(message.format(username=user))
                )
                return True
            else:
                self.logger.error("Error: {}".format(message))
                return False
        except Exception as e:
            self.logger.error("Error {}".format(e))
            return False
            




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
        d["url"] = "https://cyberoam.daiict.ac.in:8090/"
        write_hidden(d, "data.json")
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
