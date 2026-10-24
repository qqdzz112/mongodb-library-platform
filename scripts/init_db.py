#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_db.py —— 一键初始化数据库

作用：从 data/ 目录的三个 JSON 文件建库、建集合（含固定集合 / 时间序列集合 / 视图）、
      导入数据、建立索引，可选创建只读与读写账号。

用法：
    # 1) 默认：连接本机无认证的 MongoDB，建库导入
    python scripts/init_db.py

    # 2) 指定连接参数（也支持环境变量）
    python scripts/init_db.py --host 192.168.1.10 --port 27017

    # 3) 已启用 --auth 时，用管理员账号初始化并创建业务账号
    python scripts/init_db.py --user admin --password 'xxx' --auth-db admin --create-users

    # 4) 重建（先删库再导入，会清空数据！）
    python scripts/init_db.py --drop

注意：
    时间序列集合的 timeField 必须是 BSON Date 类型，因此必须用 EJSON.parse()
    而不是 JSON.parse()，否则 {"$date": "..."} 会变成普通对象而插入失败。
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure

# ------------------------------------------------------------------
# 路径
# ------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

CST = timezone(timedelta(hours=8))


# ------------------------------------------------------------------
# 工具
# ------------------------------------------------------------------
def log(msg=""):
    print(msg, flush=True)


def step(n, title):
    log()
    log("=" * 62)
    log(f"  [{n}] {title}")
    log("=" * 62)


def load_json(name):
    """读取 data/ 下的扩展 JSON 文件。

    文件里的 {"$date": "..."} 是 MongoDB 扩展 JSON，必须还原为 datetime，
    否则时间序列集合插入时会报 timeField must be a Date。
    """
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在：{path}")
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    # 优先用 bson.json_util（pymongo 自带），它完整支持 Extended JSON
    try:
        from bson import json_util
        return json_util.loads(raw)
    except ImportError:
        # 兜底：手工把 {"$date": "..."} 换成 datetime
        def _hook(obj):
            if "$date" in obj and len(obj) == 1:
                s = obj["$date"].replace("Z", "+00:00")
                return datetime.fromisoformat(s)
            return obj
        return json.loads(raw, object_hook=_hook)


def build_uri(args):
    """构造 MongoDB 连接串（密码需 URL 编码）"""
    from urllib.parse import quote_plus

    if not args.user:
        return f"mongodb://{args.host}:{args.port}/"
    return (
        f"mongodb://{quote_plus(args.user)}:{quote_plus(args.password or '')}"
        f"@{args.host}:{args.port}/?authSource={args.auth_db}"
    )


# ------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="初始化图书情报平台数据库")
    ap.add_argument("--host", default=os.getenv("MONGO_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("MONGO_PORT", "27017")))
    ap.add_argument("--db", default=os.getenv("MONGO_DB", "library"), help="业务库名")
    ap.add_argument("--user", default=os.getenv("MONGO_USER", ""), help="连接用户名（可空）")
    ap.add_argument("--password", default=os.getenv("MONGO_PASSWORD", ""), help="连接密码")
    ap.add_argument("--auth-db", default=os.getenv("MONGO_AUTH_DB", "admin"), help="认证库")
    ap.add_argument("--drop", action="store_true", help="先删除同名数据库（清空数据）")
    ap.add_argument("--expire-days", type=int, default=3650,
                    help="时间序列数据保留天数，默认 3650 天（10 年）")
    ap.add_argument("--create-users", action="store_true",
                    help="创建 libReader / libWriter 业务账号")
    ap.add_argument("--reader-pwd", default="Lab@2026", help="libReader 密码")
    ap.add_argument("--writer-pwd", default="Lab@2026", help="libWriter 密码")
    args = ap.parse_args()

    uri = build_uri(args)
    masked = uri
    if args.user:
        from urllib.parse import quote_plus
        masked = uri.replace(quote_plus(args.password or ""), "******")

    log("连接信息：" + masked)
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    # ---------- 连通性检查 ----------
    step(0, "检查连接")
    try:
        info = client.server_info()
        log(f"  连接成功  MongoDB {info['version']}")
    except Exception as e:  # noqa: BLE001
        log(f"  [失败] {e}")
        log()
        log("  请确认：")
        log("    1) mongod 已启动（ss -lntp | grep 27017）")
        log("    2) 主机端口正确")
        log("    3) 若已启用 --auth，请用 --user/--password 传入管理员账号")
        return 1

    db = client[args.db]

    # ---------- 重建 ----------
    if args.drop:
        step(0, f"删除数据库 {args.db}（--drop）")
        client.drop_database(args.db)
        log("  已删除")

    # ---------- 1. 普通集合 ----------
    step(1, "创建普通集合")
    for name in ("books", "readers", "category_stats"):
        if name in db.list_collection_names():
            log(f"  {name:<16} 已存在，跳过")
            continue
        db.create_collection(name)
        log(f"  {name:<16} 创建成功")

    # ---------- 2. 固定集合 ----------
    step(2, "创建固定集合 book_logs（1MB / 1000 条）")
    if "book_logs" in db.list_collection_names():
        log("  已存在，跳过")
    else:
        db.create_collection("book_logs", capped=True, size=1048576, max=1000)
        log("  book_logs 创建成功  capped=True size=1048576 max=1000")

    # ---------- 3. 时间序列集合 ----------
    step(3, "创建时间序列集合 borrow_logs")
    expire = args.expire_days * 86400
    if "borrow_logs" in db.list_collection_names():
        log("  已存在，检查配置")
        opt = db.get_collection("borrow_logs").options
        log(f"  当前 expireAfterSeconds = {opt.get('expireAfterSeconds')}")
    else:
        db.create_collection(
            "borrow_logs",
            timeseries={"timeField": "borrow_date", "granularity": "hours"},
            expireAfterSeconds=expire,
        )
        log(f"  borrow_logs 创建成功")
        log(f"    timeField          = borrow_date")
        log(f"    granularity        = hours")
        log(f"    expireAfterSeconds = {expire}（{args.expire_days} 天）")
        log()
        log("  说明：实训任务书要求 63072000 秒（2 年），但那样会把 2023 年的")
        log("        历史借阅记录当过期数据自动删除，导致趋势统计缺少年份。")
        log("        故默认改为 10 年，可用 --expire-days 调整。")

    # ---------- 4. 视图 ----------
    step(4, "创建视图 book_in_stock（stock > 0）")
    if "book_in_stock" in db.list_collection_names():
        log("  已存在，跳过")
    else:
        db.create_collection(
            "book_in_stock",
            viewOn="books",
            pipeline=[{"$match": {"stock": {"$gt": 0}}}],
        )
        log("  book_in_stock 创建成功  viewOn=books")

    # ---------- 5. 导入数据 ----------
    step(5, "导入 data/ 下的数据集")
    counts = {}

    # books：先 insertOne 一条，其余 insertMany
    books = load_json("books.txt")
    if db.books.count_documents({}) > 0:
        log(f"  books            已有 {db.books.count_documents()} 条，跳过导入")
    else:
        first = books[0]
        db.books.insert_one(first)
        rest = books[1:]
        if rest:
            db.books.insert_many(rest)
        log(f"  books            insertOne 1 条 + insertMany {len(rest)} 条 = {len(books)} 条")
    counts["books"] = db.books.count_documents({})

    # readers
    readers = load_json("readers.txt")
    if db.readers.count_documents({}) > 0:
        log(f"  readers          已有 {db.readers.count_documents()} 条，跳过导入")
    else:
        db.readers.insert_many(readers)
        log(f"  readers          insertMany {len(readers)} 条")
    counts["readers"] = db.readers.count_documents({})

    # borrow_logs（时间序列，必须是 Date）
    logs = load_json("borrow_logs.txt")
    if db.borrow_logs.count_documents({}) > 0:
        log(f"  borrow_logs      已有 {db.borrow_logs.count_documents()} 条，跳过导入")
    else:
        sample = logs[0]["borrow_date"]
        if not isinstance(sample, datetime):
            raise TypeError(
                f"borrow_date 不是 Date 类型（当前 {type(sample).__name__}），"
                "时间序列集合无法插入。请确认使用 bson.json_util 解析。"
            )
        db.borrow_logs.insert_many(logs)
        log(f"  borrow_logs      insertMany {len(logs)} 条（borrow_date 已还原为 Date）")
    counts["borrow_logs"] = db.borrow_logs.count_documents({})

    counts["book_in_stock"] = db.book_in_stock.count_documents({})

    # ---------- 6. 索引 ----------
    step(6, "创建索引")
    indexes = [
        ({"isbn": 1}, {"unique": True, "name": "isbn_unique"}, "isbn 唯一索引"),
        ({"title": 1}, {"name": "title_1"}, "title 单键索引"),
        ({"category": 1}, {"name": "category_1"}, "category 单键索引"),
        ({"tags": 1}, {"name": "tags_1"}, "tags 多键索引"),
        ({"category": 1, "price": -1}, {"name": "category_1_price_-1"}, "category+price 复合索引"),
    ]
    for spec, opt, desc in indexes:
        name = db.books.create_index(spec, **opt)
        log(f"  {name:<24} {desc}")
    # index_information() 返回 {索引名: 详情} 的字典
    # 注意：mongosh 里的 db.xxx.getIndexes() 是 shell 方法，PyMongo 没有，
    #       Python 端对应的是 index_information() / list_indexes()。
    log(f"  当前索引总数：{len(db.books.index_information())} 个")

    # ---------- 7. 统计结果落库（$merge）----------
    step(7, "运行 A1 分类统计并写入 category_stats（$merge）")
    db.books.aggregate([
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "avgRating": {"$avg": "$rating"},
            "maxStock": {"$max": "$stock"},
            "minStock": {"$min": "$stock"},
        }},
        {"$merge": {
            "into": "category_stats",
            "whenMatched": "replace",
            "whenNotMatched": "insert",
        }},
    ])
    counts["category_stats"] = db.category_stats.count_documents({})
    log(f"  category_stats   {counts['category_stats']} 条")

    # ---------- 8. 账号 ----------
    if args.create_users:
        step(8, "创建业务账号")
        for user, pwd, roles in [
            ("libReader", args.reader_pwd, [{"role": "read", "db": args.db}]),
            ("libWriter", args.writer_pwd,
             [{"role": "readWrite", "db": args.db}, {"role": "dbAdmin", "db": args.db}]),
        ]:
            try:
                db.command("dropUser", user)
                log(f"  {user:<12} 已存在，先删除")
            except OperationFailure:
                pass
            db.command("createUser", user, pwd=pwd, roles=roles)
            log(f"  {user:<12} 创建成功  角色：{[r['role'] for r in roles]}")
        log()
        log("  注意：这两个账号建在业务库 %s 下，" % args.db)
        log("        连接时 authSource 应填 %s 而不是 admin。" % args.db)

    # ---------- 汇总 ----------
    step(9, "初始化完成 · 数据核对")
    log(f"  数据库：{args.db}")
    log()
    log(f"  {'集合':<18}{'文档数':>8}   类型")
    log("  " + "-" * 44)
    for name in ("books", "readers", "borrow_logs", "category_stats", "book_logs", "book_in_stock"):
        infos = db.list_collection_names(filter={"name": name})
        if not infos:
            continue
        info = db.command("listCollections", filter={"name": name})["cursor"]["firstBatch"]
        typ = info[0]["type"] if info else "collection"
        label = {  # noqa: E501
            "collection": "普通集合",
            "timeseries": "时间序列集合",
            "view": "视图",
        }.get(typ, typ)
        if name == "book_logs":
            label = "固定集合"
        log(f"  {name:<18}{counts.get(name, 0):>8}   {label}")

    log()
    log("下一步：")
    log("  命令行程序：  python main.py")
    log("  Web 前端：    python web/app.py   →  http://127.0.0.1:5000")
    log()

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
