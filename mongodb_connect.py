"""
mongodb_connect.py —— MongoDB 连接模块
《图书情报检索与统计平台》

职责：封装获取数据库连接的逻辑，被所有模块（CLI 与 Flask 前端）调用。
连接参数在本模块内统一定义，支持通过环境变量覆盖，便于部署到不同环境。
"""

import os
from urllib.parse import quote_plus

from pymongo import MongoClient

# ============================================================
# 连接参数（可用环境变量覆盖，便于 GitHub 用户本地运行）
# ============================================================
MONGO_HOST = os.getenv("MONGO_HOST", "127.0.0.1")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USER = os.getenv("MONGO_USER", "libWriter")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "Lab@2026")
AUTH_DB = os.getenv("MONGO_AUTH_DB", "library")
DB_NAME = os.getenv("MONGO_DB", "library")

# 是否启用认证
#   默认 0（关闭）—— 与 scripts/init_db.py 的默认行为保持一致，
#                    这样全新克隆的用户不改任何配置就能跑通。
#   设为 1 时走 mongodb://user:pwd@host:port/db?authSource=xxx
USE_AUTH = os.getenv("MONGO_USE_AUTH", "0") not in ("0", "false", "False", "")


def _build_uri():
    """构造连接 URI。

    密码里的 @ : / ? 等字符是 URI 保留字符，必须 URL 编码。
    例如 "Lab@2026" 编码后是 "Lab%402026"，否则会被解析成
    "用户名:密码" 与 "主机" 之间的分隔符，导致认证失败。
    """
    if not USE_AUTH:
        return f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    user = quote_plus(MONGO_USER)
    pwd = quote_plus(MONGO_PASSWORD)
    return (
        f"mongodb://{user}:{pwd}@{MONGO_HOST}:{MONGO_PORT}/{DB_NAME}"
        f"?authSource={AUTH_DB}"
    )


URI = _build_uri()


class MongoDBConnect:
    """MongoDB 连接工具类（单例，避免重复建连）"""

    _client = None

    @staticmethod
    def get_connect(uri=URI):
        if MongoDBConnect._client is None:
            MongoDBConnect._client = MongoClient(
                uri, serverSelectionTimeoutMS=5000, maxPoolSize=50
            )
        return MongoDBConnect._client

    @staticmethod
    def get_database(db_name=DB_NAME):
        return MongoDBConnect.get_connect()[db_name]

    @staticmethod
    def ping():
        """返回 (是否连通, 服务器版本或错误信息)"""
        try:
            client = MongoDBConnect.get_connect()
            client.admin.command("ping")
            return True, client.server_info()["version"]
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    @staticmethod
    def close():
        if MongoDBConnect._client is not None:
            MongoDBConnect._client.close()
            MongoDBConnect._client = None
            return True
        return False
