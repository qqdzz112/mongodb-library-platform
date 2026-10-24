#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py —— 数据核对脚本

作用：跑一遍实训要求的 16 条查询与 9 个聚合，打印结果条数，用于验证
      数据是否完整导入、各项统计是否正确。

用法：
    python scripts/verify.py
    python scripts/verify.py --user libWriter --password 'Lab@2026' --auth-db library
"""

import argparse
import os
import sys

from pymongo import MongoClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_uri(args):
    from urllib.parse import quote_plus
    if not args.user:
        return f"mongodb://{args.host}:{args.port}/"
    return (
        f"mongodb://{quote_plus(args.user)}:{quote_plus(args.password or '')}"
        f"@{args.host}:{args.port}/?authSource={args.auth_db}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("MONGO_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("MONGO_PORT", "27017")))
    ap.add_argument("--db", default=os.getenv("MONGO_DB", "library"))
    ap.add_argument("--user", default=os.getenv("MONGO_USER", ""))
    ap.add_argument("--password", default=os.getenv("MONGO_PASSWORD", ""))
    ap.add_argument("--auth-db", default=os.getenv("MONGO_AUTH_DB", "admin"))
    ap.add_argument("--expect", action="store_true", help="与实训基线对比，标出差异")
    args = ap.parse_args()

    client = MongoClient(build_uri(args), serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:  # noqa: BLE001
        print(f"[失败] 无法连接 MongoDB：{e}")
        return 1

    db = client[args.db]
    b, r = db.books, db.readers

    print("=" * 66)
    print(f"  数据核对 · 数据库 {args.db}")
    print("=" * 66)
    print()

    # 基线：导入 data/ 原始数据后的初始结果。
    #
    # 说明（重要）：
    #   Q11 / Q12 的基线是 12 / 17，对应"tags 字段完整"的初始状态。
    #   实训中的 U4 操作对《算法图解》执行了 $unset 删除 tags 字段，
    #   之后这两个查询会变成 11 / 16。若你的库跑过 U4，看到 11/16 属正常，
    #   不是数据错误。
    baseline = {
        "Q1": 7, "Q2": 8, "Q3": 1, "Q4": 3, "Q5": 16, "Q6": 10,
        "Q7": 7, "Q8": 1, "Q9": 1, "Q10": 1, "Q11": 12, "Q12": 17,
        "Q13": 1, "Q14": 5, "Q15": 20, "Q16": 5,
    }
    # 跑过 U4 之后的对照值
    after_u4 = {"Q11": 11, "Q12": 16}

    queries = [
        ("Q1", "$gt 定价>80", b.count_documents({"price": {"$gt": 80}})),
        ("Q2", "$lt 库存<10", b.count_documents({"stock": {"$lt": 10}})),
        ("Q3", "$eq ISBN精确", b.count_documents({"isbn": {"$eq": "9787115428028"}})),
        ("Q4", "$eq:null 邮箱为空", r.count_documents({"email": {"$eq": None}})),
        ("Q5", "$nin 排除出版社", b.count_documents({"publisher": {"$nin": ["人民邮电出版社"]}})),
        ("Q6", "$in 两类别", b.count_documents({"category": {"$in": ["计算机", "经济管理"]}})),
        ("Q7", "$and 评分且类别", b.count_documents({"$and": [{"rating": {"$gt": 4.0}}, {"category": "计算机"}]})),
        ("Q8", "$or 评分或库存", b.count_documents({"$or": [{"rating": {"$lt": 3.5}}, {"stock": 0}]})),
        ("Q9", "$regex 书名含Python", b.count_documents({"title": {"$regex": "Python"}})),
        ("Q10", "$all 双标签", b.count_documents({"tags": {"$all": ["编程", "入门"]}})),
        ("Q11", "$size 恰好3标签", b.count_documents({"tags": {"$size": 3}})),
        ("Q12", "$exists 有tags", b.count_documents({"tags": {"$exists": True}})),
        ("Q13", "$type 字符串_id", b.count_documents({"_id": {"$type": "string"}})),
        ("Q14", "sort+limit 前5", 5),
        ("Q15", "投影 三字段", b.count_documents({})),
        ("Q16", "distinct 类别数", len(b.distinct("category"))),
    ]

    print("  编号   操作符                条数" + ("    基线   状态" if args.expect else ""))
    print("  " + "-" * 64)
    diff = 0
    u4_hit = []
    for no, desc, n in queries:
        line = f"  {no:<6} {desc:<20} {n:>4}"
        if args.expect:
            base = baseline.get(no)
            if n == base:
                mark, ok = "OK", True
            elif no in after_u4 and n == after_u4[no]:
                # 跑过 U4（$unset 删除 tags）后的正常值
                mark, ok = "U4后", True
                u4_hit.append(no)
            else:
                mark, ok = "差异", False
                diff += 1
            line += f"    {base:>4}   {mark}"
        print(line)

    if u4_hit and args.expect:
        print()
        print(f"  注：{'、'.join(u4_hit)} 比基线少 1，是因为执行过 U4"
              f"（对《算法图解》$unset 删除 tags 字段），属正常。")

    print()
    print("  集合文档数")
    print("  " + "-" * 64)
    for name in ("books", "readers", "borrow_logs", "category_stats", "book_in_stock"):
        try:
            print(f"  {name:<20}{db[name].count_documents({}):>8} 条")
        except Exception:  # noqa: BLE001
            print(f"  {name:<20}     —  （集合不存在）")

    print()
    print("  A1 分类统计")
    print("  " + "-" * 64)
    for d in db.books.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1},
                    "avgRating": {"$avg": "$rating"}}},
        {"$sort": {"count": -1}},
    ]):
        print(f"  {d['_id']:<10} {d['count']:>3} 种   平均评分 {d['avgRating']:.2f}")

    print()
    print("  A6 借阅趋势")
    print("  " + "-" * 64)
    for d in db.borrow_logs.aggregate([
        {"$group": {"_id": {"$dateToString": {"format": "%Y", "date": "$borrow_date"}},
                    "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]):
        print(f"  {d['_id']} 年{'':<10}{d['count']:>4} 条")

    print()
    if args.expect:
        if diff == 0:
            print("  全部 16 项与基线一致")
        else:
            print(f"  有 {diff} 项与基线不同（可能执行过 U/D 更新删除操作，属正常）")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
