# -*- coding: utf-8 -*-
import smtplib
from src.configs import get_setting, logger
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

setting = get_setting()


def send_mail(message: str, receiver_email: str, subject: str):
    # ========== 基本信息 ==========
    smtp_server = setting.SMTP_HOST
    smtp_port = setting.SMTP_PORT
    sender_email = setting.SENDER  # 发件人邮箱
    sender_pass = setting.SMTP_PASSWORD
    receiver_email = receiver_email  # 收件人邮箱

    # ========== 邮件内容 ==========
    subject = subject
    body = message

    # 创建 MIMEText 邮件对象（纯文本）
    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = formataddr(("0x7o7 WorkSpace", sender_email))  # 工作室名称
    message['To'] = Header(receiver_email, 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    # ========== 发送邮件 ==========
    try:
        if not sender_email or not sender_pass or not receiver_email:
            raise RuntimeError("SMTP configuration is incomplete")
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, [receiver_email], message.as_string())
        logger.info("✅ 邮件发送成功！")
    except Exception as e:
        logger.error("❌ 邮件发送失败：", e)


if __name__ == '__main__':
    send_mail(message='test', receiver_email=setting.RECEIVER, subject='用户gomatt6688@gmail.com登录成功!')
