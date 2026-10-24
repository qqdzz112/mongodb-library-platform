"""
main.py —— 图书情报检索与统计平台 主程序
《图书情报检索与统计平台》实训 · 任务五 ST-5.5

要求对照：
  ① 启动时打印数据库连接状态与各集合文档总数   -> show_startup()
  ② 菜单至少 8 个功能项，覆盖检索/统计/更新/删除 -> main_menu()
  ③ 每次数据变更后打印受影响的文档数            -> 各分支内 print
  ④ 查询无结果时给出明确提示                   -> 统一用 print_rows()
  ⑤ 退出前正确关闭数据库连接                    -> finally: close()
"""

import sys

import mongodb_connect
import book_manager
import reader_manager
import borrow_manager
import stat_manager


# ---------------- 输出辅助 ----------------
def ask(prompt=""):
    """安全输入：EOF（管道/重定向场景）时返回空串，不抛异常"""
    try:
        return input(prompt)
    except EOFError:
        return ""


def print_rows(rows, empty_hint="未查询到符合条件的数据"):
    """统一输出：空结果给明确提示，有结果逐条打印"""
    rows = list(rows) if rows is not None else []
    if not rows:
        print(f"  [空] {empty_hint}")
        return
    print(f"  共 {len(rows)} 条结果：")
    for i, r in enumerate(rows, 1):
        if isinstance(r, dict):
            parts = [f"{k}={v}" for k, v in r.items()]
            print(f"  {i:>2}. " + " | ".join(parts))
        else:
            print(f"  {i:>2}. {r}")


def show_startup():
    """① 启动时打印连接状态与各集合文档总数"""
    db = mongodb_connect.MongoDBConnect.get_database()
    ok, ver = mongodb_connect.MongoDBConnect.ping()
    print("=" * 62)
    print("  图书情报检索与统计平台  v1.0")
    print("=" * 62)
    if not ok:
        print(f"  [连接失败] {ver}")
        return False
    print(f"  [连接成功] 服务器 {mongodb_connect.MONGO_HOST}:{mongodb_connect.MONGO_PORT}"
          f"  MongoDB {ver}  数据库 {mongodb_connect.DB_NAME}")
    print("-" * 62)
    print("  集合文档总数：")
    for name in ("books", "readers", "borrow_logs", "category_stats", "book_logs", "book_in_stock"):
        try:
            print(f"    {name:<16}{db[name].count_documents({}):>6} 条")
        except Exception as e:
            print(f"    {name:<16}     -  ({e.__class__.__name__})")
    print("=" * 62)
    return True


def main_menu():
    """② 菜单，共 10 个功能项（≥8）"""
    print("""
┌──────────────────────── 功 能 菜 单 ────────────────────────┐
│  1. 按书名/ISBN 检索图书                          (检索)   │
│  2. 组合条件检索（类别/价格/评分/库存/标签）      (检索)   │
│  3. 评分排行榜 Top N                              (检索)   │
│  4. 分类统计（库存总量/均价/数量）                (统计)   │
│  5. 借阅趋势分析（按年份）                        (统计)   │
│  6. 畅销榜 / 活跃读者                             (统计)   │
│  7. 读者查询与学院统计                            (统计)   │
│  8. 借阅登记 / 归还处理                           (更新)   │
│  9. 调整图书库存                                  (更新)   │
│ 10. 清理零库存图书 / 删除指定图书                 (删除)   │
│  0. 退出                                                    │
└─────────────────────────────────────────────────────────────┘""")


# ---------------- 各功能 ----------------
def menu_1():
    print("\n[1] 检索图书 —— 输入书名关键字或 ISBN（直接回车返回）")
    kw = ask("  请输入：").strip()
    if not kw:
        return
    if kw.isdigit() or kw.upper().startswith("ISBN-"):
        doc = book_manager.find_by_isbn(kw)
        print_rows([doc] if doc else [], f"没有找到 ISBN 为 {kw} 的图书")
    else:
        print_rows(book_manager.find_by_title(kw), f"书名中不含“{kw}”的图书不存在")


def menu_2():
    print("\n[2] 组合条件检索（每项直接回车表示不限）")
    cat = ask("  类别（如 计算机）：").strip() or None
    pmin = ask("  最低价：").strip()
    rmin = ask("  最低评分：").strip()
    tags = ask("  标签（多个用逗号分隔，需同时具备）：").strip()
    rows = book_manager.search_books(
        category=cat,
        price_min=float(pmin) if pmin else None,
        rating_min=float(rmin) if rmin else None,
        tags=[t.strip() for t in tags.split(",")] if tags else None,
    )
    print_rows(rows, "没有同时满足这些条件的图书")


def menu_3():
    print_rows(book_manager.rating_ranking(5), "图书集合为空")


def menu_4():
    print("\n[4] 分类统计（按库存总量降序）")
    rows = stat_manager.category_stats()
    print_rows(rows, "图书集合为空")
    saved = list(stat_manager.save_category_stats())
    db = mongodb_connect.MongoDBConnect.get_database()
    print(f"  [落库] category_stats 现有 {db['category_stats'].count_documents({})} 条")


def menu_5():
    print("\n[5] 借阅趋势（按年份）")
    print_rows(stat_manager.borrow_trend_by_year(), "暂无借阅流水")


def menu_6():
    print("\n[6] 畅销榜（按借阅流水统计）")
    print_rows(stat_manager.bestseller_by_book(5), "暂无借阅流水")
    print("\n  活跃读者 Top5：")
    print_rows(reader_manager.active_readers(5), "暂无借阅记录")


def menu_7():
    print("\n[7] 读者查询与学院统计")
    kw = ask("  输入读者姓名关键字（直接回车跳过）：").strip()
    if kw:
        print("  读者检索结果：")
        print_rows(reader_manager.search_readers(kw), f"姓名中不含“{kw}”的读者不存在")
    print(f"\n  读者总数：{reader_manager.count_readers()} 人")
    print("  各学院人数：")
    print_rows(reader_manager.college_statistics())
    print("  借阅等级分布：")
    print_rows(reader_manager.level_distribution())


def menu_8():
    print("\n[8] 借阅登记 / 归还处理")
    print("    a) 借阅   b) 归还")
    act = ask("  请选择：").strip().lower()
    card = ask("  借阅证号：").strip()
    isbn = ask("  ISBN：").strip()
    if act == "a":
        try:
            res = borrow_manager.borrow_book(card, isbn)
            print(f"  [借阅成功] 受影响文档数 = 1（新增流水 {res.inserted_id}），库存已 -1")
        except Exception as e:
            print(f"  [借阅失败] {e}")
    else:
        res = borrow_manager.return_book(card, isbn)
        print(f"  [归还完成] 受影响文档数 = {res.modified_count}")
        if getattr(res, "message", ""):
            print(f"  [说明] {res.message}")


def menu_9():
    print("\n[9] 调整图书库存")
    isbn = ask("  ISBN：").strip()
    delta = ask("  变化量（如 -5 或 3）：").strip()
    try:
        res = book_manager.update_stock(isbn, int(delta))
        print(f"  [更新完成] 匹配 {res.matched_count} 条，受影响的文档数 = {res.modified_count}")
        doc = book_manager.find_by_isbn(isbn)
        if doc:
            print(f"  当前库存：{doc.get('stock')}")
    except ValueError:
        print("  [输入错误] 变化量必须是整数")


def menu_10():
    print("\n[10] 删除操作")
    print("    a) 清理零库存图书   b) 删除指定 ISBN 图书")
    act = ask("  请选择：").strip().lower()
    if act == "a":
        res = book_manager.delete_out_of_stock()
        print(f"  [清理完成] 受影响的文档数 = {res.deleted_count}")
    else:
        isbn = ask("  ISBN：").strip()
        res = book_manager.delete_one_by_isbn(isbn)
        print(f"  [删除完成] 受影响的文档数 = {res.deleted_count}")
        if res.deleted_count == 0:
            print("  [提示] 没有找到该 ISBN 对应的图书")


# ---------------- 主循环 ----------------
def main():
    if not show_startup():
        print("\n  请检查 mongod 是否已启动、账号密码是否正确。")
        return 1

    actions = {
        "1": menu_1, "2": menu_2, "3": menu_3, "4": menu_4, "5": menu_5,
        "6": menu_6, "7": menu_7, "8": menu_8, "9": menu_9, "10": menu_10,
    }

    # 支持非交互模式：python main.py 4 5  （便于批量演示与截图）
    if len(sys.argv) > 1:
        for key in sys.argv[1:]:
            fn = actions.get(key)
            if fn:
                fn()
            else:
                print(f"  [警告] 未知功能项 {key}")
        print("\n  [退出] 数据库连接已关闭")
        return 0

    while True:
        main_menu()
        choice = ask("  请选择功能编号：").strip()
        # 空输入 = EOF（管道输入结束）或直接回车，退出循环避免死循环
        if choice in ("0", ""):
            if choice == "":
                print("\n  [提示] 输入结束，自动退出")
            break
        fn = actions.get(choice)
        if fn:
            try:
                fn()
            except Exception as e:
                print(f"  [异常] {e.__class__.__name__}: {e}")
        else:
            print("  [提示] 请输入 0-10 之间的编号")
        if not ask("\n  按回车继续..."):
            print("\n  [提示] 输入结束，自动退出")
            break

    print("\n  感谢使用，再见。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        # ⑤ 退出前正确关闭数据库连接
        mongodb_connect.MongoDBConnect.close()
