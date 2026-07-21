#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能A股投资助手 V2 - Tornado基础Handler
"""

import tornado.web
from config import ALLOWED_ORIGINS


class BaseHandler(tornado.web.RequestHandler):
    """基础Handler，主要负责CORS"""

    def set_default_headers(self):
        origin = self.request.headers.get('origin', None)

        if ALLOWED_ORIGINS == '*':
            # 开发模式：允许所有来源
            self.set_header("Access-Control-Allow-Origin", "*")
        elif origin and origin in ALLOWED_ORIGINS.split(','):
            # 生产模式：只允许配置的来源（精确匹配）
            self.set_header("Access-Control-Allow-Origin", origin)
            self.set_header("Access-Control-Allow-Credentials", "true")

        self.set_header("Access-Control-Allow-Methods", "POST, GET, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers",
                       "Content-Type, X-Requested-With, X-Xsrftoken")
        self.set_header("Access-Control-Max-Age", "86400")

    def options(self):
        """处理CORS预检请求"""
        self.set_status(204)
        self.finish()

    def write_error(self, status_code, **kwargs):
        """统一错误响应格式为JSON"""
        self.set_header("Content-Type", "application/json")
        if status_code == 404:
            self.write({'code': 404, 'message': 'Not Found', 'data': None})
        elif status_code == 500:
            self.write({'code': 500, 'message': 'Internal Server Error', 'data': None})
        else:
            self.write({'code': status_code, 'message': 'Error', 'data': None})
