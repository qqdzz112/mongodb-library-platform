"""
library_data.py —— 前端数据访问层

所有查询集中在这里，Flask 路由只负责取数据和渲染。
查询全部为只读操作（find / aggregate / count），不修改数据库。
"""

import os
import sys

# 让 web/ 能引用项目根目录下共用的 mongodb_connect.py
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import mongodb_connect  # noqa: E402


def _db():
    return mongodb_connect.MongoDBConnect.get_database()


# ============================================================
#  概览统计
# ============================================================
def overview():
    """首页仪表盘数据"""
    db = _db()
    ok, ver = mongodb_connect.MongoDBConnect.ping()

    books = db.books
    total_books = books.count_documents({})
    in_stock = books.count_documents({"stock": {"$gt": 0}})
    out_of_stock = books.count_documents({"stock": 0})

    # 平均评分、平均价格、总库存量
    stat = list(books.aggregate([
        {"$group": {
            "_id": None,
            "avgRating": {"$avg": "$rating"},
            "avgPrice": {"$avg": "$price"},
            "totalStock": {"$sum": "$stock"},
            "totalBorrow": {"$sum": "$borrow_count"},
        }}
    ]))
    s = stat[0] if stat else {}

    return {
        "connected": ok,
        "server_version": ver,
        "total_books": total_books,
        "total_readers": db.readers.count_documents({}),
        "total_logs": db.borrow_logs.count_documents({}),
        "in_stock": in_stock,
        "out_of_stock": out_of_stock,
        "category_count": len(books.distinct("category")),
        "avg_rating": round(s.get("avgRating") or 0, 2),
        "avg_price": round(s.get("avgPrice") or 0, 2),
        "total_stock": s.get("totalStock", 0),
        "total_borrow": s.get("totalBorrow", 0),
    }


# ============================================================
#  图书
# ============================================================
def list_books(keyword=None, category=None, min_rating=None,
               price_min=None, price_max=None, sort="rating",
               page=1, per_page=12):
    """图书列表：支持关键字、类别、评分、价格区间筛选与分页"""
    conds = []
    if keyword:
        # 书名 / 作者 / ISBN 任一匹配
        conds.append({"$or": [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"author": {"$regex": keyword, "$options": "i"}},
            {"isbn": {"$regex": keyword, "$options": "i"}},
        ]})
    if category:
        conds.append({"category": category})
    if min_rating is not None:
        conds.append({"rating": {"$gte": min_rating}})
    price = {}
    if price_min is not None:
        price["$gte"] = price_min
    if price_max is not None:
        price["$lte"] = price_max
    if price:
        conds.append({"price": price})

    query = {"$and": conds} if conds else {}

    sort_map = {
        "rating": [("rating", -1), ("borrow_count", -1)],
        "price_asc": [("price", 1)],
        "price_desc": [("price", -1)],
        "borrow": [("borrow_count", -1)],
        "title": [("title", 1)],
    }
    sort_spec = sort_map.get(sort, sort_map["rating"])

    total = _db().books.count_documents(query)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    cursor = (
        _db().books.find(query, {"_id": 0})
        .sort(sort_spec)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    return {
        "rows": list(cursor),
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def get_book(isbn):
    """按 ISBN 查单本图书"""
    return _db().books.find_one({"isbn": isbn}, {"_id": 0})


def book_borrow_records(isbn, limit=20):
    """某本书的借阅记录"""
    return list(_db().borrow_logs.find(
        {"book_isbn": isbn},
        {"_id": 0, "reader_card": 1, "borrow_date": 1, "return_date": 1, "status": 1}
    ).sort("borrow_date", -1).limit(limit))


def categories():
    """全部类别（带数量）"""
    return list(_db().books.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]))


# ============================================================
#  统计
# ============================================================
def category_stats():
    """分类统计：数量、平均评分、库存总量、价格区间"""
    return list(_db().books.aggregate([
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "avgRating": {"$avg": "$rating"},
            "avgPrice": {"$avg": "$price"},
            "totalStock": {"$sum": "$stock"},
            "maxStock": {"$max": "$stock"},
            "minStock": {"$min": "$stock"},
        }},
        {"$sort": {"count": -1, "_id": 1}},
    ]))


def borrow_trend():
    """按年份的借阅趋势"""
    return list(_db().borrow_logs.aggregate([
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y", "date": "$borrow_date"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]))


def top_borrowed(limit=10):
    """畅销榜：按借阅流水统计被借次数"""
    return list(_db().borrow_logs.aggregate([
        {"$group": {"_id": "$book_isbn", "times": {"$sum": 1}}},
        {"$sort": {"times": -1, "_id": 1}},
        {"$limit": limit},
        {"$lookup": {
            "from": "books",
            "localField": "_id",
            "foreignField": "isbn",
            "as": "book",
        }},
        {"$unwind": "$book"},
        {"$project": {
            "_id": 0,
            "isbn": "$_id",
            "title": "$book.title",
            "author": "$book.author",
            "category": "$book.category",
            "rating": "$book.rating",
            "times": 1,
        }},
    ]))


def college_ranking():
    """学院借阅量排行"""
    return list(_db().borrow_logs.aggregate([
        {"$group": {"_id": "$reader_card", "n": {"$sum": 1}}},
        {"$lookup": {
            "from": "readers",
            "localField": "_id",
            "foreignField": "card_no",
            "as": "r",
        }},
        {"$unwind": "$r"},
        {"$group": {
            "_id": "$r.college",
            "total": {"$sum": "$n"},
            "readers": {"$sum": 1},
        }},
        {"$sort": {"total": -1, "_id": 1}},
    ]))


def status_distribution():
    """借阅状态分布"""
    return list(_db().borrow_logs.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))


# ============================================================
#  读者
# ============================================================
def list_readers(keyword=None, college=None, page=1, per_page=12):
    """读者列表"""
    conds = []
    if keyword:
        conds.append({"$or": [
            {"name": {"$regex": keyword, "$options": "i"}},
            {"card_no": {"$regex": keyword, "$options": "i"}},
        ]})
    if college:
        conds.append({"college": college})
    query = {"$and": conds} if conds else {}

    total = _db().readers.count_documents(query)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    items = list(
        _db().readers.find(query, {"_id": 0})
        .sort([("card_no", 1)])
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    # 附带每位读者的借阅次数
    for it in items:
        it["borrowCount"] = _db().borrow_logs.count_documents({"reader_card": it["card_no"]})

    return {
        "rows": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def colleges():
    """全部学院（带人数）"""
    return list(_db().readers.aggregate([
        {"$group": {"_id": "$college", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]))


def level_distribution():
    """借阅等级分布"""
    return list(_db().readers.aggregate([
        {"$group": {"_id": "$level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))


# ============================================================
#  借阅流水
# ============================================================
def list_logs(status=None, keyword=None, page=1, per_page=15):
    """借阅流水列表"""
    conds = []
    if status:
        conds.append({"status": status})
    if keyword:
        conds.append({"$or": [
            {"reader_card": {"$regex": keyword, "$options": "i"}},
            {"book_isbn": {"$regex": keyword, "$options": "i"}},
        ]})
    query = {"$and": conds} if conds else {}

    total = _db().borrow_logs.count_documents(query)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    items = list(
        _db().borrow_logs.find(query)
        .sort("borrow_date", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    # 补图书名和读者名
    isbns = {it["book_isbn"] for it in items if it.get("book_isbn")}
    cards = {it["reader_card"] for it in items if it.get("reader_card")}
    book_map = {b["isbn"]: b["title"] for b in
                _db().books.find({"isbn": {"$in": list(isbns)}}, {"isbn": 1, "title": 1})}
    reader_map = {r["card_no"]: r["name"] for r in
                  _db().readers.find({"card_no": {"$in": list(cards)}}, {"card_no": 1, "name": 1})}
    for it in items:
        it["book_title"] = book_map.get(it.get("book_isbn"), "（已下架）")
        it["reader_name"] = reader_map.get(it.get("reader_card"), "（未知）")
        it["_id"] = str(it["_id"])

    return {
        "rows": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def log_statuses():
    """全部借阅状态"""
    return [s for s in _db().borrow_logs.distinct("status") if s]
