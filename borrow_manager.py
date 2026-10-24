"""
borrow_manager.py —— 借阅管理模块
《图书情报检索与统计平台》实训 · 任务五 ST-5.3

功能：借阅登记、归还处理、逾期查询
涉及方法：insert_one、update_many、find

【重要实现说明】
borrow_logs 是**时间序列集合**（timeField = borrow_date），MongoDB 对它有两条硬性限制：
  1. 没有 metaField 时，**不允许对已有文档做 update/delete**（报 code 72）
  2. 时间序列文档不可原地修改时间字段
因此在时间序列模型下，"归还"与"标记逾期"不能靠 update 改状态字段，
本模块改为**写入新流水**的方式表达状态流转（append-only），并同步更新 books 的库存。
这样既符合时间序列"只追加"的设计本意，也绕开了 MongoDB 的限制。
"""

from datetime import datetime, timedelta, timezone
import mongodb_connect

_CST = timezone(timedelta(hours=8))


def _logs():
    return mongodb_connect.MongoDBConnect.get_database()["borrow_logs"]


def _books():
    return mongodb_connect.MongoDBConnect.get_database()["books"]


def _now():
    """返回带时区的当前时间（Bson Date）"""
    return datetime.now(_CST)


def _open_borrows(reader_card, book_isbn):
    """找出某读者某书尚未归还的借阅流水（借出 或 逾期）"""
    return list(_logs().find({
        "reader_card": reader_card,
        "book_isbn": book_isbn,
        "status": {"$in": ["借出", "逾期"]},
    }).sort("borrow_date", -1))


def borrow_book(reader_card, book_isbn, days=30):
    """借阅登记（insert_one）

    写入一条"借出"流水，同时把 books 的 stock-1、borrow_count+1。
    """
    book = _books().find_one({"isbn": book_isbn})
    if not book:
        raise ValueError(f"图书不存在: {book_isbn}")
    if book.get("stock", 0) <= 0:
        raise ValueError(f"《{book['title']}》库存不足，无法借阅")

    doc = {
        "borrow_date": _now(),
        "reader_card": reader_card,
        "book_isbn": book_isbn,
        "status": "借出",
        "due_date": _now() + timedelta(days=days),
    }
    res = _logs().insert_one(doc)
    _books().update_one({"isbn": book_isbn}, {"$inc": {"stock": -1, "borrow_count": 1}})
    return res


def return_book(reader_card, book_isbn):
    """归还处理

    时间序列集合不支持 update 已有文档，故以"追加一条已归还流水"的方式表达归还，
    并回补库存。返回一个带 modified_count 的简易结果对象，便于 main.py 统一打印。
    """
    opens = _open_borrows(reader_card, book_isbn)
    if not opens:
        return _SimpleResult(0, "没有找到待归还的借阅记录")

    latest = opens[0]
    doc = {
        "borrow_date": latest["borrow_date"],          # 保持原借阅时间
        "return_date": _now(),
        "reader_card": reader_card,
        "book_isbn": book_isbn,
        "status": "已归还",
        "origin_id": latest["_id"],
    }
    _logs().insert_one(doc)

    # 如果有"借出"状态的旧流水，无法 update，直接以新流水为准；库存回补 1
    _books().update_one({"isbn": book_isbn}, {"$inc": {"stock": 1}})
    return _SimpleResult(1, f"已生成归还流水，库存 +1（原借阅于 {latest['borrow_date'].date()}）")


def mark_overdue(due_before=None):
    """标记逾期（时间序列下同样以追加流水实现）

    把仍为"借出"且超过 due_date 的记录，各追加一条"逾期"状态流水。
    """
    due_before = due_before or _now()
    pendings = list(_logs().find({
        "status": "借出",
        "due_date": {"$lt": due_before},
    }))
    n = 0
    for p in pendings:
        _logs().insert_one({
            "borrow_date": p["borrow_date"],
            "reader_card": p["reader_card"],
            "book_isbn": p["book_isbn"],
            "status": "逾期",
            "origin_id": p["_id"],
        })
        n += 1
    return _SimpleResult(n, f"标记逾期 {n} 条")


def find_overdue(limit=50):
    """查询逾期记录（find）"""
    return list(_logs().find(
        {"status": "逾期"},
        {"_id": 0, "reader_card": 1, "book_isbn": 1, "borrow_date": 1, "return_date": 1, "status": 1}
    ).limit(limit))


def find_by_reader(reader_card):
    """查询某读者的全部借阅流水（find）"""
    return list(_logs().find(
        {"reader_card": reader_card},
        {"_id": 0, "book_isbn": 1, "borrow_date": 1, "return_date": 1, "status": 1}
    ).sort("borrow_date", -1))


def count_logs(query=None):
    """借阅流水总数"""
    return _logs().count_documents(query or {})


class _SimpleResult:
    """简易结果对象，模拟 pymongo 的 UpdateResult 接口（only 供 main.py 打印）"""

    def __init__(self, modified_count=0, message=""):
        self.modified_count = modified_count
        self.matched_count = modified_count
        self.message = message
