#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
智能A股投资助手 V2 - Tornado主入口
基于stock项目架构，从头构建增强版
"""

import os
import sys
import re
import json
import logging
from datetime import datetime

import tornado.web
import tornado.ioloop
import tornado.httpserver
import tornado.options

# 设置路径
sys.path.insert(0, os.path.dirname(__file__))

from handlers import (
    BaseHandler,
    IndicatorsHandler,
    IndicatorListHandler,
    BacktestHandler,
    BacktestSingleHandler,
    SelectionHandler,
    SelectionOnlyHandler,
    StockAnalysisHandler,
    NewsHandler
)
from config import (
    get_stock_cache_path, get_historical_dir,
    DEBUG_MODE, API_PORT, _resolve_cookie_secret
)
COOKIE_SECRET = _resolve_cookie_secret() or 'dev-temp-secret-not-for-production'

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'v2.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HomeHandler(BaseHandler):
    """首页"""

    def get(self):
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        index_path = os.path.join(static_path, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            self.write(f.read())


class HealthHandler(BaseHandler):
    """健康检查"""

    def get(self):
        self.write(json.dumps({
            'status': 'ok',
            'version': 'V2.0',
            'timestamp': datetime.now().isoformat()
        }))


class StockListHandler(BaseHandler):
    """选股结果列表"""

    def get(self):
        """返回选股结果（从缓存读取）"""
        try:
            cache_file = str(get_stock_cache_path())

            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.write(json.dumps({
                    'code': 0,
                    'message': 'success',
                    'data': data
                }))
            else:
                self.write(json.dumps({
                    'code': 404,
                    'message': '选股结果不存在，请先运行选股',
                    'data': None
                }))

        except Exception as e:
            logger.error(f"获取选股结果失败: {e}")
            self.send_error(500)


class StockDetailHandler(BaseHandler):
    """股票详情"""

    def get(self, code):
        """返回单只股票详情"""
        # 验证股票代码格式，防止路径遍历攻击
        if not re.match(r'^\d{6}$', code):
            self.send_error(400)
            return

        try:
            data_dir = str(get_historical_dir())
            filepath = os.path.join(data_dir, f"{code}.json")

            if not os.path.exists(filepath):
                self.send_error(404)
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)

            # 获取最新两条数据
            data = content.get('data', [])
            latest = data[-1] if data else {}
            prev = data[-2] if len(data) >= 2 else latest

            # ‌仍 P0 修复: 为避免前端调用此接口时无法计算涨跌幅, 在 latest 中补上 prev_close
            latest_with_prev = dict(latest) if latest else {}
            if 'prev_close' not in latest_with_prev and prev:
                latest_with_prev['prev_close'] = prev.get('close', 0)

            self.write(json.dumps({
                'code': 0,
                'message': 'success',
                'data': {
                    'code': code,
                    'name': content.get('name', code),
                    'latest': latest_with_prev,
                    'total_days': len(content.get('data', []))
                }
            }))

        except Exception as e:
            logger.error(f"获取股票详情失败: {e}")
            self.send_error(500)


class DataTableHandler(BaseHandler):
    """数据表格页面"""

    def get(self):
        table_name = self.get_argument('table_name', 'stock_zh_a_spot_em')
        self.render("table.html",
                   table_name=table_name,
                   version="V2.0")


class Application(tornado.web.Application):
    """Tornado应用"""

    def __init__(self):
        handlers = [
            # 主页
            (r"/", HomeHandler),
            (r"/index", HomeHandler),

            # 健康检查
            (r"/api/health", HealthHandler),

            # 选股结果
            (r"/api/stocks", StockListHandler),
            (r"/api/stock/([^/]+)", StockDetailHandler),

            # 指标图表
            (r"/api/indicators/config", IndicatorListHandler),
            (r"/api/indicators/([^/]+)", IndicatorsHandler),

            # 回测
            (r"/api/backtest", BacktestHandler),
            (r"/api/backtest/([^/]+)", BacktestSingleHandler),

            # 选股
            (r"/api/selection", SelectionHandler),
            (r"/api/selection/only", SelectionOnlyHandler),
            (r"/api/analyze/([0-9]{6})", StockAnalysisHandler),

            # 早间资讯
            (r"/api/news", NewsHandler),

            # 数据表格
            (r"/data/table", DataTableHandler),
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            static_url_prefix='/static/',
            xsrf_cookies=True,  # 启用XSRF保护
            cookie_secret=COOKIE_SECRET,
            debug=DEBUG_MODE,
            default_encoding='utf-8',
        )

        super().__init__(handlers, **settings)

        logger.info("智能A股投资助手 V2 启动完成")


def main():
    tornado.options.parse_command_line()

    # 生产环境配置校验
    from config import validate_production_config
    validate_production_config()

    # 启动定时任务调度器
    try:
        from scheduler import start_scheduler
        scheduler = start_scheduler()
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}")

    port = API_PORT
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(port)

    logger.info(f"服务运行在 http://localhost:{port}")
    logger.info(f"API文档: http://localhost:{port}/api/health")

    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
