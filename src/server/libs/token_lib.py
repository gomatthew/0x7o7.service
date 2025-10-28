# -*- coding: utf-8 -*-
import datetime
import jwt
from src.configs import get_setting
from src.server.db.repository import get_user_by_id

settings = get_setting()


class TokenHandleJWT(object):

    # 生成 token
    @staticmethod
    def generate_token(user_id):

        try:
            payload = {
                'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=settings.TOKEN_EXPIRE_HOURS),
                'iat': datetime.datetime.now(datetime.UTC),
                'iss': '0x7o7',
                'data': {
                    'id': user_id,
                }
            }

            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            return token, settings.TOKEN_EXPIRE_HOURS

        except Exception as e:
            return e

    # 验证 token
    @staticmethod
    def verify_token(token: str):

        # token 是否为空
        if token is None:
            return None

        try:
            payload = jwt.decode(token, settings.SECRET_KEY)

            if payload is None:
                return None

            user_id = payload['data']['id']
            user = get_user_by_id(user_id)
            if user.token is None:
                return None

            if user.token != token:
                return None

            return payload

        # 过期 token
        except jwt.ExpiredSignatureError:
            return None

        # 无效 token
        except jwt.InvalidTokenError:
            return None

        except BaseException as e:
            print(e)
            return None

    # 获取 token
    # @staticmethod
    # def get_token():
    #
    #     try:
    #         header = request.headers.get('Authorization')
    #
    #         if header is None:
    #             return None
    #
    #         authorizations = header.split(';')
    #
    #         data = ''
    #         for authorization in authorizations:
    #             if 'token=' in authorization:
    #                 data = authorization
    #
    #         token_list = data.split('=')
    #
    #         if token_list is None or token_list[0] != 'token' or len(token_list) != 2:
    #             return None
    #
    #         token = token_list[1]
    #
    #         return token
    #
    #     except BaseException as e:
    #         print(e)
    #         return None

    # # 获取app_key
    # @staticmethod
    # def get_app_key():
    #     try:
    #         header = request.headers.get('Authorization')
    #         authorizations = header.split(';')
    #
    #         data = ''
    #         for authorization in authorizations:
    #             if 'appKey=' in authorization:
    #                 data = authorization
    #
    #         token_list = data.split('=')
    #
    #         if token_list is None or token_list[0] != 'appKey' or len(token_list) != 2:
    #             return None
    #
    #         token = token_list[1]
    #
    #         return token
    #
    #     except BaseException as e:
    #         print(e)
    #         return None
    #
    # # 获取微信app_key
    # @staticmethod
    # def get_wechat_app_id():
    #     try:
    #         header = request.headers.get('Authorization')
    #         authorizations = header.split(';')
    #
    #         data = ''
    #         for authorization in authorizations:
    #             if 'appId=' in authorization:
    #                 data = authorization
    #
    #         wechat_app_id_list = data.split('=')
    #
    #         if wechat_app_id_list is None or wechat_app_id_list[0] != 'appId' or len(wechat_app_id_list) != 2:
    #             return None
    #
    #         wechat_app_id = wechat_app_id_list[1]
    #
    #         return wechat_app_id
    #
    #     except BaseException as e:
    #         print(e)
    #         return None
    #
    # # 获取app_id
    # def get_app_id(self):
    #
    #     app_key = self.get_app_key()
    #     apps = Apps.query.filter(Apps.key == app_key).first()
    #
    #     if apps is None:
    #         return None
    #
    #     app_id = apps.id
    #
    #     return app_id


token_handler = TokenHandleJWT()
