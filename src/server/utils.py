# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText
from email.header import Header


def send_mail():
    # ========== 基本信息 ==========
    smtp_server = 'smtp.163.com'       # 163邮箱SMTP服务器地址
    smtp_port = 465                    # SSL端口
    sender_email = 'mjmj1124@163.com' # 发件人邮箱
    sender_pass = 'KGSDjuaCNegAhRkH'     # 授权码（不是邮箱登录密码）
    receiver_email = 'gomatt6688@gmail.com'  # 收件人邮箱

    # ========== 邮件内容 ==========
    subject = '来自Python的问候 - 163邮箱测试'
    body = '你好，这是用Python通过163邮箱发送的测试邮件。'

    # 创建 MIMEText 邮件对象（纯文本）
    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = Header("Python发信人", 'utf-8') # 工作室名称
    message['To'] = Header("gomatt6688@gmail.com", 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    # ========== 发送邮件 ==========
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, [receiver_email], message.as_string())
        print("✅ 邮件发送成功！")
    except Exception as e:
        print("❌ 邮件发送失败：", e)
