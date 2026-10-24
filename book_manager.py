"""
book_manager.py —— 图书管理模块
《图书情报检索与统计平台》实训 · 任务五 ST-5.3

功能：图书增删改查、条件检索、评分排行
涉及方法：insert_one、insert_many、find、find_one、update_one、delete_one、delete_many
"""

from pymongo import ASCENDING, DESCENDING
import mongodb_connect


def _books():
    return mongodb_connect.MongoDBConnect.get_database()["books"]


# ---------------- 增 ----------------
def add_one_book(doc):
    """新增单本图书（insert_one）"""
    return _books().insert_one(doc)


def add_many_books(docs):
    """批量新增图书（insert_many）"""
    return _books().insert_many(docs)


# ---------------- 查 ----------------
def find_by_title(keyword):
    """按书名模糊查询（$regex）"""
    return list(_books().find({"title": {"$regex": keyword}}, {"_id": 0, "title": 1, "author": 1,
                                                                "publisher": 1, "price": 1, "rating": 1}))


def find_by_isbn(isbn):
    """按 ISBN 精确查询（find_one）"""
    return _books().find_one({"isbn": isbn}, {"_id": 0})


def search_books(category=None, price_min=None, price_max=None,
                 rating_min=None, stock_max=None, tags=None):
    """组合条件检索（$and + 范围操作符 + $all）"""
    conds = []
    if category:
        conds.append({"category": category})
    if price_min is not None:
        conds.append({"price": {"$gte": price_min}})
    if price_max is not None:
        conds.append({"price": {"$lte": price_max}})
    if rating_min is not None:
        conds.append({"rating": {"$gte": rating_min}})
    if stock_max is not None:
        conds.append({"stock": {"$lte": stock_max}})
    if tags:
        conds.append({"tags": {"$all": tags}})
    query = {"$and": conds} if conds else {}
    return list(_books().find(query, {"_id": 0, "title": 1, "category": 1, "price": 1,
                                      "rating": 1, "stock": 1}))


def rating_ranking(limit=5):
    """评分排行榜（sort + limit，并列时按借阅次数次序键稳定排序）"""
    return list(
        _books()
        .find({}, {"_id": 0, "title": 1, "rating": 1, "borrow_count": 1})
        .sort([("rating", DESCENDING), ("borrow_count", DESCENDING)])
        .limit(limit)
    )


def count_books(query=None):
    """统计图书数量（count_documents）"""
    return _books().count_documents(query or {})


def distinct_categories():
    """获取所有类别（distinct）"""
    return sorted(_books().distinct("category"))


# ---------------- 改 ----------------
def update_stock(isbn, delta):
    """调整库存（update_one + $inc）"""
    return _books().update_one({"isbn": isbn}, {"$inc": {"stock": delta}})


def update_price_ratio(category, ratio):
    """某类别价格按比例调整（update_many + $mul）"""
    return _books().update_many({"category": category}, {"$mul": {"price": ratio}})


def touch_book(isbn):
    """更新最后修改时间（update_one + $currentDate）"""
    return _books().update_one({"isbn": isbn}, {"$currentDate": {"last_updated": {"$type": "date"}}})


# ---------------- 删 ----------------
def delete_one_by_isbn(isbn):
    """删除单本图书（delete_one + $eq）"""
    return _books().delete_one({"isbn": {"$eq": isbn}})


def delete_out_of_stock():
    """清理零库存图书（delete_many）"""
    return _books().delete_many({"stock": 0})
