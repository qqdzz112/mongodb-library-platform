"""
stat_manager.py —— 统计分析模块
《图书情报检索与统计平台》实训 · 任务五 ST-5.4

功能：分类统计、借阅趋势、畅销榜
涉及方法：aggregate（聚合管道）
"""

import mongodb_connect


def _db():
    return mongodb_connect.MongoDBConnect.get_database()


# ---------------- ST-5.4 分类统计 ----------------
def category_stats():
    """按类别分组：库存总量、平均价格、图书数量，按库存总量降序（ST-5.4 要求）"""
    return list(_db()["books"].aggregate([
        {"$group": {
            "_id": "$category",
            "totalStock": {"$sum": "$stock"},
            "avgPrice": {"$avg": "$price"},
            "bookCount": {"$sum": 1},
            "avgRating": {"$avg": "$rating"},
            "maxStock": {"$max": "$stock"},
            "minStock": {"$min": "$stock"},
        }},
        {"$sort": {"totalStock": -1, "_id": 1}},
        {"$project": {
            "_id": 0,
            "类别": "$_id",
            "库存总量": "$totalStock",
            "平均价格": {"$round": ["$avgPrice", 2]},
            "图书数量": "$bookCount",
            "平均评分": {"$round": ["$avgRating", 2]},
            "最高库存": "$maxStock",
            "最低库存": "$minStock",
        }}
    ]))


# ---------------- ST-5.4 借阅趋势 ----------------
def borrow_trend_by_year():
    """按年份分组统计借阅量，格式化输出“2024年”"""
    return list(_db()["borrow_logs"].aggregate([
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y年", "date": "$borrow_date"}},
            "借阅量": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "年份": "$_id", "借阅量": 1}}
    ]))


def borrow_trend_by_month(year=2024):
    """按月份统计指定年份的借阅量"""
    return list(_db()["borrow_logs"].aggregate([
        {"$match": {"borrow_date": {"$gte": __import__("datetime").datetime(year, 1, 1),
                                    "$lt": __import__("datetime").datetime(year + 1, 1, 1)}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$borrow_date"}},
            "借阅量": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]))


# ---------------- ST-5.4 畅销榜 ----------------
def bestseller_by_book(limit=10):
    """畅销榜：按实际借阅流水统计被借次数最多的图书"""
    return list(_db()["borrow_logs"].aggregate([
        {"$group": {"_id": "$book_isbn", "borrowTimes": {"$sum": 1}}},
        {"$sort": {"borrowTimes": -1, "_id": 1}},
        {"$limit": limit},
        {"$lookup": {"from": "books", "localField": "_id",
                     "foreignField": "isbn", "as": "book"}},
        {"$unwind": "$book"},
        {"$project": {"_id": 0, "isbn": "$_id", "书名": "$book.title",
                      "类别": "$book.category", "被借次数": "$borrowTimes"}}
    ]))


def top_borrow_count(limit=10):
    """畅销榜（按 books.borrow_count 累计字段排序）"""
    return list(_db()["books"].find(
        {}, {"_id": 0, "title": 1, "borrow_count": 1, "category": 1}
    ).sort("borrow_count", -1).limit(limit))


# ---------------- 其他统计 ----------------
def publisher_top5():
    """出版社图书数量前 5（$topN 等价写法）"""
    return list(_db()["books"].aggregate([
        {"$group": {"_id": "$publisher", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": 5}
    ]))


def sales_estimation(limit=5):
    """销售额估算 = 单价 × 借阅次数，保留两位小数"""
    return list(_db()["books"].aggregate([
        {"$project": {"_id": 0, "书名": "$title",
                      "销售额": {"$round": [{"$multiply": ["$price", "$borrow_count"]}, 2]}}},
        {"$sort": {"销售额": -1}},
        {"$limit": limit}
    ]))


def save_category_stats():
    """把分类统计结果写入 category_stats 集合（$merge）"""
    return _db()["books"].aggregate([
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "avgRating": {"$avg": "$rating"},
            "maxStock": {"$max": "$stock"},
            "minStock": {"$min": "$stock"},
        }},
        {"$merge": {"into": "category_stats",
                    "whenMatched": "replace", "whenNotMatched": "insert"}}
    ])
