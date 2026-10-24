"""
reader_manager.py —— 读者管理模块
《图书情报检索与统计平台》实训 · 任务五 ST-5.3

功能：读者信息管理、学院统计、等级分布
涉及方法：find、count_documents、distinct
"""

import mongodb_connect


def _readers():
    return mongodb_connect.MongoDBConnect.get_database()["readers"]


def find_by_card(card_no):
    """按借阅证号查询读者"""
    return _readers().find_one({"card_no": card_no}, {"_id": 0})


def search_readers(keyword):
    """按姓名模糊查询读者"""
    return list(_readers().find(
        {"name": {"$regex": keyword}},
        {"_id": 0, "card_no": 1, "name": 1, "college": 1, "level": 1}
    ))


def count_readers():
    """读者总数（count_documents）"""
    return _readers().count_documents({})


def college_statistics():
    """各学院读者人数统计（aggregate 按学院分组）"""
    return list(_readers().aggregate([
        {"$group": {"_id": "$college", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}}
    ]))


def level_distribution():
    """借阅等级分布（distinct + 计数）"""
    result = []
    for level in sorted(_readers().distinct("level")):
        n = _readers().count_documents({"level": level})
        result.append({"_id": level, "count": n})
    return result


def active_readers(limit=5):
    """活跃读者榜单（关联借阅流水，aggregate + $lookup）"""
    db = mongodb_connect.MongoDBConnect.get_database()
    return list(db["borrow_logs"].aggregate([
        {"$group": {"_id": "$reader_card", "borrowCount": {"$sum": 1}}},
        {"$sort": {"borrowCount": -1, "_id": 1}},
        {"$limit": limit},
        {"$lookup": {"from": "readers", "localField": "_id",
                     "foreignField": "card_no", "as": "reader"}},
        {"$unwind": "$reader"},
        {"$project": {"_id": 0, "card_no": "$_id", "name": "$reader.name",
                      "college": "$reader.college", "borrowCount": 1}}
    ]))


def college_borrow_ranking():
    """学院借阅量排行榜（ST-4 A8 的 Python 实现）"""
    db = mongodb_connect.MongoDBConnect.get_database()
    return list(db["borrow_logs"].aggregate([
        {"$group": {"_id": "$reader_card", "borrowCount": {"$sum": 1}}},
        {"$lookup": {"from": "readers", "localField": "_id",
                     "foreignField": "card_no", "as": "reader"}},
        {"$unwind": "$reader"},
        {"$group": {"_id": "$reader.college",
                    "totalBorrows": {"$sum": "$borrowCount"},
                    "readerCount": {"$sum": 1}}},
        {"$sort": {"totalBorrows": -1, "_id": 1}}
    ]))
