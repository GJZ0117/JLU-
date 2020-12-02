import time
import smtplib
from email.mime.text import MIMEText
import pymysql
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 数据库配置参数
DBIP = ''
DBUSER = ''
DBPWD = ''
DATABASE = ''


# 每天凌晨刷新数据库finish字段为0
def refreshDB():
    conn = pymysql.connect(DBIP, DBUSER, DBPWD, DATABASE)
    cursor = conn.cursor()
    sql = "update jkdk set finish=0"
    try:
        cursor.execute(sql)
        conn.commit()
    except Exception as e:
        print(e)
        refreshDB()
    finally:
        conn.close()
        return "refresh database finish"


# 发送打卡成功邮件通知
def sendSuccessEmail(EmailList, userlist):
    # 发送方邮箱
    msg_from = ""
    # 发送方邮箱授权码
    passwd = ""
    s = smtplib.SMTP_SSL("smtp.qq.com", 465)
    s.login(msg_from, passwd)

    # 发送打卡成功邮件
    num = len(EmailList)
    for i in range(num):
        try:
            now = time.asctime(time.localtime(time.time()))
            subject = "打卡成功!"
            content = userlist[i] + "健康打卡成功!\n" + str(now)
            msg = MIMEText(content)
            msg['Subject'] = subject
            msg['From'] = msg_from

            s.sendmail(msg_from, EmailList[i], msg.as_string())
        except Exception as e:
            print(EmailList[i] + " send scuccess email error")
    s.quit()


# 早上9点仍未打卡成功发送失败邮件
def sendFailEmail():
    # 发送方邮箱
    msg_from = ""
    # 发送方邮箱授权码
    passwd = ""
    s = smtplib.SMTP_SSL("smtp.qq.com", 465)
    s.login(msg_from, passwd)

    conn = pymysql.connect(DBIP, DBUSER, DBPWD, DATABASE)
    cursor = conn.cursor()
    sql = "select username, email_addr from jkdk where finish=0"
    cursor.execute(sql)
    backinfo = cursor.fetchall()

    num = len(backinfo)

    for i in range(num):
        username = backinfo[i][0]
        email = backinfo[i][1]
        try:
            now = time.asctime(time.localtime(time.time()))
            subject = "打卡失败!"
            content = username + " 健康打卡失败, 请自行登陆打卡!\n" + str(now)
            msg = MIMEText(content)
            msg['Subject'] = subject
            msg['From'] = msg_from

            s.sendmail(msg_from, email, msg.as_string())
        except Exception as e:
            print(email + " send fail email error")

    conn.close()
    s.quit()


# selenium自动化打卡
def work(username, password):
    driver = webdriver.Firefox()
    driver.get("https://ehall.jlu.edu.cn")

    try: 
        username_box = driver.find_element_by_id("username")
        password_box = driver.find_element_by_id("password")
        login_button = driver.find_element_by_id("login-submit")
        username_box.send_keys(username)
        password_box.send_keys(password)
        login_button.click()
        time.sleep(3)
        JKDK_button = driver.find_element_by_xpath("/html/body/div[1]/div[2]/div/ul/li[1]")
        JKDK_button.click()
        driver.switch_to.window(driver.window_handles[1])
    except Exception:
        driver.quit()
        return None

    def tryCommit(driver):
        try:
            driver.refresh()
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//ul[@class="commandBar"]/li[@class="command_li color0"]'))
            )
            normal_button = driver.find_elements_by_xpath('//input[@id="V1_CTRL28"]')[0]
            time.sleep(2)
            js="var q=document.documentElement.scrollTop=10000"
            driver.execute_script(js)
            normal_button.click()
            submit_button.click()
            ok_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//button[contains(text(),"Ok")]'))
            )
            ok_button.click()
            if ok_button != None: return username
        except Exception as e:
            print(e)
            print(str(time.asctime(time.localtime(time.time()))), "bot fail to work for", username)
    
    try:
        username = tryCommit(driver)
        driver.quit()
        return username
    except Exception:driver.quit()


# 从数据库中读数据准备打卡
def beginBot():
    conn = pymysql.connect(DBIP, DBUSER, DBPWD, DATABASE)
    cursor = conn.cursor()
    sql = 'select username, password, email_addr from jkdk where `finish`=0'
    cursor.execute(sql)
    backinfo = cursor.fetchall()

    # finish全为1所有用户已完成打卡
    if backinfo == (): 
        print(str(time.asctime(time.localtime(time.time()))), "all userscomplete daka")
        conn.close()
        return "complete"

    finish_user_list = []
    finish_email_list = []
    for info in backinfo:
        username = info[0]
        password = info[1]
        email_addr = info[2]
        try:
            is_finish = work(username, password)
            if is_finish != None:
                finish_user_list.append(username)
                finish_email_list.append(email_addr)
        except:pass

    if finish_user_list == []:
        conn.close()
        return None

    print(str(time.asctime(time.localtime(time.time()))), "bot finish work", finish_user_list)

    # 发送打卡成功邮件通知
    sendSuccessEmail(finish_email_list, finish_user_list)
    print(str(time.asctime(time.localtime(time.time()))), "send success email complete", finish_email_list)

    # 更新数据库打卡成功的记录
    finish_string = ""
    for user in finish_user_list:
        finish_string += "'" + user + "', "
    finish_string = "(" + finish_string[:-2] + ")"
    sql = "update jkdk set finish=1 where username in %s" % finish_string
    try:
        cursor.execute(sql)
        conn.commit()
        print(str(time.asctime(time.localtime(time.time()))), "update database about success users")
    except Exception as e:
        print(e)
    finally:
        conn.close()


def main():

    repeatTimes = 0

    while True:

        # 当前时间(小时)
        localhour = time.localtime(time.time())[3]

        # 早上六点到九点启动打卡机器人
        if (localhour == 6 or localhour == 7 or localhour == 8) and repeatTimes < 5:
            repeatTimes += 1
            backinfo = beginBot()
            # 全部账号完成打卡
            if backinfo == "complete":
                time.sleep(60 * 60)
            pass

        # 每天早上九点对未打卡成功的账号发邮件通知自行打卡
        elif localhour == 9:
            sendFailEmail()
            print(str(time.asctime(time.localtime(time.time()))), "send fail email complete")
            time.sleep(60 * 60)
            pass

        # 每天凌晨一点刷新数据库finish字段
        if localhour == 1:
            repeatTimes = 0
            refresh_info = refreshDB()
            if refresh_info == "refresh database finish":
                print(str(time.asctime(time.localtime(time.time()))) + "refresh database and repeatTimes complete")
                time.sleep(60 * 60)

        # 暂停一分钟
        time.sleep(60)


if __name__ == '__main__':
    main()
