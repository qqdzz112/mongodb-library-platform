"""
app.py —— 图书情报检索与统计平台 · Web 前端

技术栈：Flask + Bootstrap 5 + PyMongo
功能：只读展示 —— 仪表盘、图书检索、图书详情、统计分析、读者、借阅流水

运行（在项目根目录执行）：
    pip install -r requirements.txt
    python web/app.py
    浏览器打开 http://127.0.0.1:5000
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_WEB = os.path.dirname(os.path.abspath(__file__))
if _WEB not in sys.path:
    sys.path.insert(0, _WEB)

from flask import Flask, render_template, request  # noqa: E402

import library_data as data  # noqa: E402

app = Flask(__name__)


# ============================================================
#  模板过滤器
# ============================================================
@app.template_filter("dt")
def fmt_datetime(value, fmt="%Y-%m-%d"):
    """日期格式化，兼容 None"""
    if not value:
        return "—"
    try:
        return value.strftime(fmt)
    except Exception:  # noqa: BLE001
        return str(value)


@app.template_filter("stars")
def fmt_stars(value):
    """评分转星星字符。

    只用 ★ 和 ☆ 两个常见字符：整数部分给实心星，其余补空心星。
    0.5 分不单独表示（避免生僻字符在部分字体下显示为方框）。
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    v = max(0.0, min(5.0, v))
    full = int(round(v))          # 四舍五入到整数星数
    return "★" * full + "☆" * (5 - full)


@app.template_filter("money")
def fmt_money(value):
    try:
        return f"¥{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


# ============================================================
#  路由
# ============================================================
@app.route("/")
def index():
    """仪表盘"""
    ov = data.overview()
    return render_template(
        "index.html",
        ov=ov,
        cats=data.category_stats(),
        trend=data.borrow_trend(),
        top=data.top_borrowed(5),
        colleges=data.college_ranking(),
    )


@app.route("/books")
def books():
    """图书列表 + 检索"""
    keyword = request.args.get("q", "").strip() or None
    category = request.args.get("category", "").strip() or None
    sort = request.args.get("sort", "rating")
    page = request.args.get("page", 1, type=int)

    rating_raw = request.args.get("min_rating", "").strip()
    min_rating = float(rating_raw) if rating_raw else None
    pmin_raw = request.args.get("price_min", "").strip()
    pmax_raw = request.args.get("price_max", "").strip()
    price_min = float(pmin_raw) if pmin_raw else None
    price_max = float(pmax_raw) if pmax_raw else None

    result = data.list_books(
        keyword=keyword, category=category, min_rating=min_rating,
        price_min=price_min, price_max=price_max,
        sort=sort, page=page,
    )
    return render_template(
        "books.html",
        result=result,
        cats=data.categories(),
        q=keyword or "",
        category=category or "",
        sort=sort,
        min_rating=rating_raw,
        price_min=pmin_raw,
        price_max=pmax_raw,
    )


@app.route("/books/<isbn>")
def book_detail(isbn):
    """图书详情"""
    book = data.get_book(isbn)
    if not book:
        return render_template("404.html", message=f"没有找到 ISBN 为 {isbn} 的图书"), 404
    return render_template(
        "book_detail.html",
        book=book,
        logs=data.book_borrow_records(isbn),
    )


@app.route("/stats")
def stats():
    """统计分析"""
    return render_template(
        "stats.html",
        cats=data.category_stats(),
        trend=data.borrow_trend(),
        top=data.top_borrowed(10),
        colleges=data.college_ranking(),
        statuses=data.status_distribution(),
        levels=data.level_distribution(),
    )


@app.route("/readers")
def readers():
    """读者列表"""
    keyword = request.args.get("q", "").strip() or None
    college = request.args.get("college", "").strip() or None
    page = request.args.get("page", 1, type=int)

    result = data.list_readers(keyword=keyword, college=college, page=page)
    return render_template(
        "readers.html",
        result=result,
        colleges=data.colleges(),
        q=keyword or "",
        college=college or "",
    )


@app.route("/logs")
def logs():
    """借阅流水"""
    status = request.args.get("status", "").strip() or None
    keyword = request.args.get("q", "").strip() or None
    page = request.args.get("page", 1, type=int)

    result = data.list_logs(status=status, keyword=keyword, page=page)
    return render_template(
        "logs.html",
        result=result,
        statuses=data.log_statuses(),
        status=status or "",
        q=keyword or "",
    )


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html", message="页面不存在"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("404.html", message=f"服务器内部错误：{e}"), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    print("=" * 60)
    print("  图书情报检索与统计平台 · Web 前端")
    print(f"  访问地址： http://127.0.0.1:{port}")
    print(f"  监听地址： {host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
