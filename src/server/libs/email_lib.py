# -*- coding: utf-8 -*-
import smtplib
from src.configs import get_setting, logger
from email.mime.text import MIMEText
from email.header import Header

setting = get_setting()


def send_mail(message: str, receiver_email: str, subject: str):
    # ========== 基本信息 ==========
    smtp_server = 'smtp.163.com'  # 163邮箱SMTP服务器地址
    smtp_port = 465  # SSL端口
    sender_email = setting.SENDER  # 发件人邮箱
    sender_pass = setting.Mail163PASS  # 授权码（不是邮箱登录密码）
    receiver_email = receiver_email  # 收件人邮箱

    # ========== 邮件内容 ==========
    subject = subject
    body = message

    # 创建 MIMEText 邮件对象（纯文本）
    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = Header("0x7o7 WorkSpace", 'utf-8')  # 工作室名称
    message['To'] = Header("gomatt6688@gmail.com", 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    # ========== 发送邮件 ==========
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, [receiver_email], message.as_string())
        logger.info("✅ 邮件发送成功！")
    except Exception as e:
        logger.error("❌ 邮件发送失败：", e)


# if __name__ == '__main__':
#     send_mail()
