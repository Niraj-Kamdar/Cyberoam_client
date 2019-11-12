import os
import urllib.request
from time import sleep

from selenium.webdriver import PhantomJS
from selenium.webdriver.support.wait import WebDriverWait


def internet_on():
    try:
        urllib.request.urlopen("http://216.58.192.142", timeout=1)  # google.com
        return True
    except Exception:
        try:
            urllib.request.urlopen("http://172.217.166.174", timeout=1)  # google.com
            return True
        except Exception:
            try:
                urllib.request.urlopen("http://google.com", timeout=2)
                return True
            except Exception:
                return False


def main():

    while True:
        try:
            driver = False
            login = False
            ur = os.environ.get("STUDENTID")
            ps = os.environ.get("PASSKEY")
            try:
                driver = PhantomJS(r"./bin/phantomjs.exe")
                wait = WebDriverWait(driver, timeout=10)
                driver.get("http://cyberoam.daiict.ac.in:8090")
            except Exception as e:
                print(e)
                if driver:
                    driver.quit()
                sleep(10)
                continue
            usern = driver.find_element_by_name("username")
            passw = driver.find_element_by_name("password")
            usern.send_keys(ur)
            passw.send_keys(ps)
            login = driver.find_element(by="id", value="loginbutton")
            login.click()
            status = driver.find_element(by="id", value="statusmessage")
            status = status.get_attribute("innerHTML")
            if status == "Login failed. You have reached the maximum login limit.":
                print(status)
                driver.quit()
                sleep(1)
                continue
            else:
                sleep(1)
                status = driver.find_element(by="id", value="signin-caption")
                status = status.get_attribute("innerHTML")
                print(status)
                i = 0
                while internet_on():
                    print("internet working for {} minutes.".format(i))
                    i += 1
                    sleep(60)
                login.click()
                driver.quit()
                continue
        except Exception as e:
            print(e)

        finally:
            print("exiting application")
            if driver is not None:
                if login:
                    login.click()
                driver.quit()


if __name__ == "__main__":
    main()
