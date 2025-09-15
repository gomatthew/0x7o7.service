# -*- coding: utf-8 -*-
import qrcode

url = "http://192.168.1.173:5173/"
img = qrcode.make(url)
img.save("qrcode.png")