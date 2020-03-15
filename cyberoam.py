import ctypes
import json
import logging
import os
import re
import sys
from time import sleep, time
from xml.dom.minidom import parseString

from PyQt5 import uic
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMenu,
                             QSystemTrayIcon,
                             QWidget)
from cryptography.fernet import Fernet
from requests import Session

form_1, base_1 = uic.loadUiType('assets/dialog.ui')


def write_hidden(data, file_name):
    HIDDEN = 0x02
    if os.path.isfile(file_name):
        os.remove(file_name)
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
        self.pause = False  # pause loop
        try:
            with open("cyberoam.log", "r"):
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
        self.browser = Session()

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

    # noinspection SpellCheckingInspection
    def relogin(self):
        data = {"mode": "192",
                "username": self.studid,
                "a": str(int(time() * 1000))}
        try:
            self.logger.warning("Sending ack request...")
            response = self.browser.get(f"{self.url}live", params=data)
            data = response.content
            dom = parseString(data)
            xmlTag = dom.getElementsByTagName('ack')[0].toxml()
            message = re.search(r"\[[A-Z a-z{}.]*\]", xmlTag).group(0)
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
        data = {"mode": "193",
                "username": self.studid,
                "a": str(int(time() * 1000))}
        try:
            self.logger.warning("Sending logout request...")
            response = self.browser.post(f"{self.url}logout.xml", data=data)
            data = response.content
            dom = parseString(data)
            xmlTag = dom.getElementsByTagName('message')[0].toxml()
            message = re.search(r"\[[A-Z a-z.&#39;]*\]", xmlTag).group(0)
            self.logger.warning(message)
        except Exception as e:
            self.logger.error("Error: {}".format(e))

    def login(self):
        data = {"mode": "191",
                "username": self.studid,
                "password": self.passwd,
                "a": str(int(time() * 1000))}
        try:
            response = self.browser.post(f"{self.url}login.xml", data=data)
            data = response.content
            dom = parseString(data)
            xmlTag = dom.getElementsByTagName('message')[0].toxml()
            message = re.search(r"\[[A-Z a-z{}.]*\]", xmlTag).group(0)
            xmlTag = dom.getElementsByTagName('status')[0].toxml()
            status = re.search(r"\[[A-Z a-z{}.]*\]", xmlTag).group(0)
            if 'live' in status.lower():
                self.logger.warning(
                        "Login: {}".format(message.format(username=self.studid))
                )
                return True
            else:
                self.logger.error("Error: {}".format(message))
                return False
        except Exception as e:
            self.logger.error("Error {}".format(e))
            return False


class SetPass(base_1, form_1):
    def __init__(self):
        super(base_1, self).__init__()
        self.setupUi(self)
        self.submit.accepted.connect(self.handleSubmit)
        self.submit.rejected.connect(self.hide)

    def handleSubmit(self):
        key = Fernet.generate_key()
        f = Fernet(key)
        d = dict()
        d["Build_data"] = key.decode()
        d["STUDENTID"] = f.encrypt(self.useredit.text().encode()).decode()
        d["PASSKEY"] = f.encrypt(self.passedit.text().encode()).decode()
        d["url"] = self.urledit.text()
        d["startup"] = self.startup.isChecked()
        try:
            write_hidden(d, "data.json")
        except Exception as e:
            print(e)


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
