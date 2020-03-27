import os
import platform
import time
from http import cookiejar

import requests
from requests import RequestException

#from zhihu.conf import config

"""
扫码登录知乎，并保存cookies(默认保存到桌面cookies文件夹啊)
用知乎APP(APP-->我的，右上角)扫描二维码登录知乎。
小提示：知乎扫码特别慢，建议使用微信扫码，按屏幕提示继续操作也可登录。
"""

__all__ = ['cookies_file', 'ZhihuAccount']

# cookies默认保存路径
c_p = os.path.join(os.path.expanduser('~'), 'Desktop', 'cookies')
if not os.path.exists(c_p):
    os.makedirs(c_p)

cookies_file = os.path.join(c_p, 'cookies.txt')


class ZhihuAccount:
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'
    BASE_HEAD = {
        'Host': 'www.zhihu.com',
        'User-Agent': UA
    }

    # 登录状态码
    LOGIN_SUC = 1
    LOGIN_FAI = 0

    def __init__(self):
        self.session = requests.Session()
        self.session.cookies = cookiejar.LWPCookieJar(filename=cookies_file)
        try:
            self.session.cookies.load(ignore_discard=True)
        except FileNotFoundError:
            pass

    def sign_in(self):
        if self.sign_status() == ZhihuAccount.LOGIN_SUC:
            print('已登录！')
        else:
            print('开始登录...')
            if self.__login():
                if self.sign_status() == ZhihuAccount.LOGIN_SUC:
                    self.session.cookies.save()
                    print('登录成功！')
                    return
            print('登录失败！')

    def sign_out(self):
        if self.sign_status() == ZhihuAccount.LOGIN_SUC:
            self.session.get('https://www.zhihu.com/logout',
                             headers=ZhihuAccount.BASE_HEAD, allow_redirects=False)
            self.session.cookies.save()
        print('已退出！')

    def sign_status(self):
        """检查登录状态"""

        resp = self.session.get('https://www.zhihu.com/signup',
                                headers=ZhihuAccount.BASE_HEAD, allow_redirects=False)

        if resp.status_code == 302:
            return ZhihuAccount.LOGIN_SUC
        else:
            return ZhihuAccount.LOGIN_FAI

    def __login(self):
        """
        登录流程，返回流程是否完整执行(True/False)
        """
        try:
            # 依次访问以下链接获得各种cookies
            self.session.get("https://www.zhihu.com/signup?next=%2F",
                             headers=ZhihuAccount.BASE_HEAD)

            captcha_head = {"Referer": "https://www.zhihu.com/"}
            captcha_head.update(ZhihuAccount.BASE_HEAD)
            self.session.get("https://www.zhihu.com/api/v3/oauth/captcha?lang=en",
                             headers=captcha_head)

            resp = self.session.post("https://www.zhihu.com/udid", headers=ZhihuAccount.BASE_HEAD)

            token_head = {
                'Origin': 'https://www.zhihu.com',
                'Referer': 'https://www.zhihu.com/signup?next=%2F',
                'x-udid': resp.content.decode('utf8')
            }

            token_head.update(ZhihuAccount.BASE_HEAD)
            resp = self.session.post("https://www.zhihu.com/api/v3/account/api/login/qrcode",
                                     headers=token_head)

            token = resp.json().get('token')

            # 请求二维码
            qr = self.session.get(
                f'https://www.zhihu.com/api/v3/account/api/login/qrcode/{token}/image',
                headers=token_head)

            self.__show_qr_code(qr.content)

            print('操作系统已使用关联程序显示二维码，请使用知乎APP扫描。\n'
                  '小提示：知乎APP扫码特别慢，建议使用微信扫描，按屏幕提示继续操作也可登录。\n')

            # 检查二维码扫描状态
            time.sleep(10)
            start = time.time()
            while True:
                rjs = self.session.get(
                    f'https://www.zhihu.com/api/v3/account/api/login/qrcode/{token}/scan_info',
                    headers=captcha_head).json()
                # 登录成功后返回的数据包含user_id等
                # 用户在APP取消登录返回的状态码(status)是6
                # 登录成功后再次检查登录状态会返回错误信息，表示已登录
                if rjs.get('user_id', None) or rjs.get('status', None) == 6 or rjs.get('error'):
                    break
                # 用户有60秒的时间扫码并并确认登录，超时就退出。
                if time.time() - start >= 60:
                    print('登录超时！(<90s)')
                    break
                time.sleep(2)

            return True
        except RequestException as e:
            return False

    @staticmethod
    def __show_qr_code(image):
        """
        展示二维码供用户扫描
        """
        image_file = os.path.abspath('QR.jpg')

        with open(image_file, 'wb') as foo:
            foo.write(image)

        if platform.system() == 'Darwin':
            os.subprocess.call(['open', image_file])
        elif platform.system() == 'Linux':
            os.subprocess.call(['xdg-open', image_file])
        else:
            os.startfile(image_file)

    def __enter__(self):
        self.sign_in()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sign_out()


if __name__ == '__main__':
    with ZhihuAccount() as acc:
        # do something
        pass