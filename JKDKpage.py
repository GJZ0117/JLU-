from flask import Flask, request, render_template
import pymysql


import re
import time
import requests
import smtplib
from email.mime.text import MIMEText
import warnings
warnings.filterwarnings("ignore")


# 数据库参数
DBIP = ''
DBUSER = ''
DBPWD = ''
DATABASE = ''


app = Flask('JKDK')


# 注册时测试邮箱
def testEmail(email_addr):
    # 发送方邮箱
    msg_from = ""
    # 发送方邮箱授权码
    passwd = ""
    s = smtplib.SMTP_SSL("smtp.qq.com", 465)
    s.login(msg_from, passwd)
    # print("login successful")
    subject = "JLU健康打卡"
    content = "恭喜您注册成功JLU健康打卡机器人"
    try:
        msg = MIMEText(content)
        msg['Subject'] = subject
        msg['From'] = msg_from
        s.sendmail(msg_from, email_addr,msg.as_string())
        return "ok"
    except Exception:pass


# 测试登陆账号密码是否正确
def testAccount(username, password):
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0"
    # 从首页中获取pid
    ses = requests.session()
    index_url = "https://ehall.jlu.edu.cn/"
    headers = {
        "authority": "ehall.jlu.edu.cn",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9",
        "user-agent": user_agent,
        "upgrade-insecure-requests": "1"
    }

    try:res = ses.get(url=index_url, headers=headers)
    except Exception:res = ses.get(url=index_url, headers=headers, verify=False)

    html = res.content.decode("utf-8")
    pid = re.search('name="pid" value="[0-9|a-z|A-Z]*"', html).group()[18:-1]
    login_url = res.history[-1].headers["Location"]
    # 登陆
    headers = {
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9",
        "user-agent": user_agent,
    }
    data = {
        "username": username,
        "password": password,
        "pid": pid,
        "source": ""
    }

    try:res = ses.post(url=login_url, headers=headers, data=data)
    except Exception:res = ses.post(url=login_url, headers=headers, data=data, verify=False)

    html = res.content.decode("utf-8")
    try:
        name = re.search(r'loginName: "[^"]*"', html).group()[12:-1]
        return name
    except Exception:
        return None


def testRepeat(username, password):
    sql = "select * from jkdk where username='%s'" % username
    cursor.execute(sql)
    if cursor.fetchall() == ():return "ok"
    else:return "repeat"


# 返回登陆首页
@app.route('/jkdk/')
def JKDK():
    if request.method == "GET":
        return render_template('jkdk.html')


# 接收post传来的账号密码邮箱
@app.route('/checkuser/', methods=['POST', 'GET'])
def checkPwd():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email_addr = request.form["email_addr"]

        account_test = testAccount(username, password)
        if account_test == None: return "<h1 style='text-align:center;margin-top:10vh;'>账号或密码错误</h1>"
        repeat_test = testRepeat(username, password)
        if repeat_test == "repeat": return "<h1 style='text-align:center;margin-top:10vh;'>当前账号已注册</h1>"
        email_test = testEmail(email_addr)
        if email_test == None: return "<h1 style='text-align:center;margin-top:10vh;'>填入的邮箱暂时不可用</h1>"
        
        enter_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        finish = 0
        sql = 'insert into jkdk values ("%s", "%s", "%s", "%s", "%s", %d)' % (username, password, account_test, email_addr, enter_date, finish)
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            print("insert error")
            return "<h1 style='text-align:center;margin-top:10vh;'> " + "服务器数据库异常请联系管理员 " + "<h1>"

        return "<h1 style='text-align:center;margin-top:10vh;'> " + account_test + " 注册成功 <h1>"


if __name__ == '__main__':
    conn = pymysql.connect(DBIP, DBUSER, DBPWD, DATABASE)
    cursor = conn.cursor()
    print('已成功连接数据库')

    app.run("", "")

    cursor.close()
    conn.close()
    print('数据库连接已关闭')