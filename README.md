<div align="center">

# 图书情报检索与统计平台

**Library Information Retrieval & Statistics Platform**

基于 MongoDB 7.0 + PyMongo + Flask 的图书馆管理系统实训项目

[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PyMongo](https://img.shields.io/badge/PyMongo-4.x-13AA52)](https://pymongo.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

命令行程序 + Web 前端双界面 · 固定集合 / 时间序列集合 / 视图 / 聚合管道 / 索引优化 / 权限控制

</div>

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [技术亮点](#技术亮点)
- [查询示例](#查询示例)
- [常见问题](#常见问题)
- [许可证](#许可证)

---

## 项目简介

本项目是《NoSQL数据库技术与应用（第2版）》第 3 章「MongoDB 基础操作」的综合实训成果，实现了
一个从数据建模、检索统计到应用开发的完整图书馆情报平台。

**核心内容：**

| 模块 | 说明 |
|---|---|
| 数据建模 | 4 个业务集合 + 固定集合 + 时间序列集合 + 视图 |
| 检索功能 | 16 条查询覆盖 `$gt` `$lt` `$eq` `$ne` `$in` `$nin` `$and` `$or` `$regex` `$all` `$size` `$exists` `$type` 等操作符 |
| 更新删除 | `updateOne` / `updateMany` / `replaceOne` + `$inc` `$mul` `$currentDate` `$unset` |
| 统计分析 | 9 条聚合管道，含 `$group` `$topN` `$sortByCount` `$multiply` `$dateToString` `$lookup` `$merge` |
| 索引优化 | 唯一索引、单键、多键、复合索引，附 `explain` 性能对比 |
| 权限控制 | `read` 只读账号与 `readWrite` + `dbAdmin` 读写账号，验证权限隔离 |
| 应用开发 | 命令行菜单程序（10 项功能）+ Flask Web 前端（7 个页面） |

---

## 功能特性

### 命令行程序 `main.py`

```
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
└─────────────────────────────────────────────────────────────┘
```

支持**非交互模式**，便于批量演示：`python main.py 3 4 5`

### Web 前端 `web/app.py`

| 页面 | 路由 | 内容 |
|---|---|---|
| 仪表盘 | `/` | 统计卡片、分类分布、借阅趋势、热度榜、学院排行 |
| 图书检索 | `/books` | 关键字 / 类别 / 评分 / 价格区间筛选、排序、分页 |
| 图书详情 | `/books/<isbn>` | 完整信息、标签、借阅记录、快捷跳转 |
| 统计分析 | `/stats` | 分类统计表、趋势图、状态分布、Top10、学院榜、等级分布 |
| 读者 | `/readers` | 读者列表、按姓名/学院筛选、借阅次数 |
| 借阅流水 | `/logs` | 全部流水、按状态筛选、关联图书与读者名称 |

界面基于 **Bootstrap 5**，响应式布局，无需前端构建工具。

---

## 技术栈

| 层次 | 技术 |
|---|---|
| 数据库 | MongoDB 7.0（副本集/单机均可） |
| 驱动 | PyMongo 4.x（含 `bson.json_util`） |
| 后端 | Python 3.9+ |
| Web 框架 | Flask 3.x |
| 前端 | Bootstrap 5.3 + Bootstrap Icons（CDN 引入） |
| 模板 | Jinja2 |

---

## 快速开始

### 前置要求

- 已安装并启动 **MongoDB 5.0 或更高版本**（本项目使用 7.0）
- Python **3.9+**
- pip

### 三步跑起来

```bash
# 1) 克隆并安装依赖
git clone https://github.com/<your-name>/mongodb-library-platform.git
cd mongodb-library-platform
pip install -r requirements.txt

# 2) 初始化数据库（建集合、导数据、建索引）
python scripts/init_db.py

# 3) 启动 Web 前端
python web/app.py
```

浏览器打开 **http://127.0.0.1:5000** 即可。

### 启动命令行程序

```bash
python main.py          # 交互式菜单
python main.py 3 4 5    # 非交互，直接跑功能 3/4/5
```

### 核对数据

```bash
python scripts/verify.py --expect
```

输出 16 条查询结果与基线对比，确认数据完整。

### 启用认证（可选）

默认连接无认证的本地 MongoDB。若你的实例已开 `--auth`：

```bash
# 用管理员账号初始化并创建业务账号
python scripts/init_db.py --user admin --password 'your-pwd' --auth-db admin --create-users

# 之后连接时指定业务账号
export MONGO_USE_AUTH=1
export MONGO_USER=libWriter
export MONGO_PASSWORD='Lab@2026'
export MONGO_AUTH_DB=library
python web/app.py
```

> **注意 `authSource`**：`libReader` / `libWriter` 建在 `library` 库下，
> 因此 `MONGO_AUTH_DB=library`，不是 `admin`。填错会 `Authentication failed`。

---

## 项目结构

```
mongodb-library-platform/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── .env.example
│
├── data/                        # 数据集（扩展 JSON）
│   ├── books.txt                #   20 条图书
│   ├── readers.txt              #   16 条读者
│   └── borrow_logs.txt          #   66 条借阅流水
│
├── scripts/
│   ├── init_db.py               # 一键建库 + 导数据 + 建索引 + 建账号
│   └── verify.py                # 数据核对（16 条查询 vs 基线）
│
├── mongodb_connect.py           # 连接封装（供 CLI 与 Web 共用）
├── book_manager.py              # 图书管理
├── reader_manager.py            # 读者管理
├── borrow_manager.py            # 借阅管理
├── stat_manager.py              # 统计分析
├── main.py                      # 命令行主程序
│
├── web/
│   ├── app.py                   # Flask 应用与路由
│   ├── library_data.py          # 数据访问层（只读查询）
│   └── templates/
│       ├── base.html            # 布局与导航
│       ├── index.html           # 仪表盘
│       ├── books.html           # 图书检索
│       ├── book_detail.html     # 图书详情
│       ├── stats.html           # 统计分析
│       ├── readers.html         # 读者列表
│       ├── logs.html            # 借阅流水
│       └── 404.html             # 错误页
│
└── docs/                        # 实训文档
    ├── 项目上下文摘要.md
    ├── 操作代码总索引.md
    ├── 任务一~六操作代码.md
    └── 执行记录.md
```

---

## 数据模型

### books（图书信息，20 条）

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` | ObjectId / String | 大部为 ObjectId，有 1 条为字符串 `"ISBN-OLD-0001"` |
| `isbn` | String | ISBN-13，**唯一索引** |
| `title` | String | 书名 |
| `author` | String | 作者 |
| `publisher` | String | 出版社 |
| `category` | String | 类别（计算机/文学/经济管理/数学/外语） |
| `price` | Double | 定价 |
| `stock` | Int | 库存 |
| `rating` | Double | 评分 0—5 |
| `tags` | Array\<String\> | 标签数组（**多键索引**） |
| `publish_date` | Date | 出版日期 |
| `borrow_count` | Int | 累计借阅次数 |
| `last_updated` | Date | 最后更新时间（部分文档有） |

### readers（读者信息，16 条）

`card_no` `name` `college` `email`（部分为 null）`phone` `level` `register_date` `fav_categories[]`

### borrow_logs（借阅流水，**时间序列集合**）

| 字段 | 类型 | 说明 |
|---|---|---|
| `borrow_date` | Date | **timeField**，必须是 Date 类型 |
| `return_date` | Date | 归还时间（部分有） |
| `reader_card` | String | 关联 readers.card_no |
| `book_isbn` | String | 关联 books.isbn |
| `status` | String | 借出 / 已归还 / 逾期 |

> 时间序列参数：`timeField=borrow_date`，`granularity=hours`，`expireAfterSeconds=315360000`（10 年）

### category_stats（统计结果，5 条）

`_id`（类别）`count` `avgRating` `maxStock` `minStock` —— 由 `$merge` 写入

### 特殊集合

| 集合 | 类型 | 参数 |
|---|---|---|
| `book_logs` | 固定集合 | `capped=true, size=1048576, max=1000` |
| `borrow_logs` | 时间序列 | `timeField=borrow_date, granularity=hours` |
| `book_in_stock` | 视图 | `viewOn=books, pipeline=[{$match:{stock:{$gt:0}}}]` |

### 索引

| 索引名 | 字段 | 类型 |
|---|---|---|
| `_id_` | `_id` | 默认主键 |
| `isbn_unique` | `isbn` | **唯一索引** |
| `title_1` | `title` | 单键 |
| `category_1` | `category` | 单键 |
| `tags_1` | `tags` | **多键**（数组每元素一条索引项） |
| `category_1_price_-1` | `category` + `price` | **复合**（遵循前缀原则） |

---

## 技术亮点

实现过程中遇到的真实问题与解法，都不只是"跑通"，而是"想清楚为什么"。

### 1. 时间序列集合不允许 update 已有文档

```text
pymongo.errors.WriteError: Cannot perform an update on a time-series collection
that does not have a metaField (code 72)
```

**原因**：`borrow_logs` 是无 `metaField` 的时间序列集合，MongoDB 禁止对已有文档
执行 `update` / `delete`。

**解法**：把"归还"改为 **append-only** 追加模式 —— 新增一条 `status="已归还"` 的流水，
用 `origin_id` 指向原记录，同时回补库存。这反而更贴合时间序列"只追加、不原地更新"
的设计本意。

### 2. 2 年过期窗口会吃掉历史数据

任务书要求 `expireAfterSeconds = 63072000`（2 年）。但数据集最早记录是 2023-01，
若在 2026 年运行，2 年窗口会把 2023 全年数据当作过期记录自动清除，趋势统计直接缺年份。

**解法**：默认改为 **10 年**（`--expire-days` 可调），并在 `init_db.py` 里显式说明原因。

### 3. 启用 `--auth` 前必须先建管理员

若 `admin` 库为空就带 `--auth` 重启，将无法执行任何管理操作，连创建账号都做不到。

**解法**：`init_db.py --create-users` 会先建业务账号；管理员账号需在无认证状态下先建好。

### 4. 评分排行存在并列

评分序列为 `4.9, 4.8, 4.8, 4.8, 4.7, 4.7, 4.7`，取前 5 时第 5 与第 6 名同为 4.7，
只按 `rating` 排序结果不稳定。

**解法**：补 `borrow_count` 作次序键 —— `sort({rating:-1, borrow_count:-1})`，保证结果唯一可复现。

### 5. 连接串里的密码必须 URL 编码

密码 `Lab@2026` 中的 `@` 是 URI 保留字符，直接拼接会被当成"用户名密码"与"主机"的
分隔符，导致认证失败。

**解法**：`quote_plus("Lab@2026")` → `Lab%402026`。

### 6. `$unset` 对不存在的字段静默成功

对没有 `tags` 字段的文档执行 `$unset` 不会报错，`modifiedCount` 返回 `0`。
容易误判为"删除成功"。

**解法**：判断是否删除成功要看**字段是否消失**，而不是只看 `modifiedCount`。

### 7. 必须用 `EJSON` / `json_util` 解析扩展 JSON

`JSON.parse` 会把 `{"$date": "2023-04-01..."}` 解析成普通对象，
插入时间序列集合时报 `timeField must be a Date`。

**解法**：使用 `bson.json_util.loads()`，正确还原为 `datetime`。

---

## 查询示例

### 基础检索

```javascript
// Q1 定价 80 元以上
db.books.find({price: {$gt: 80}})

// Q4 邮箱为空的读者（$eq: null 同时匹配 null 与字段不存在）
db.readers.find({email: {$eq: null}})

// Q6 属于计算机或经济管理（$in）
db.books.find({category: {$in: ["计算机", "经济管理"]}})
```

### 组合与高级检索

```javascript
// Q7 评分 4.0 以上且计算机类（$and）
db.books.find({$and: [{rating: {$gt: 4.0}}, {category: "计算机"}]})

// Q10 同时带"编程"和"入门"两个标签（$all）
db.books.find({tags: {$all: ["编程", "入门"]}})

// Q11 恰好 3 个标签（$size 只能写整数）
db.books.find({tags: {$size: 3}})
```

### 聚合统计

```javascript
// A1 按类别统计数量与平均评分
db.books.aggregate([
  {$group: {
    _id: "$category",
    count: {$sum: 1},
    avgRating: {$avg: "$rating"},
    maxStock: {$max: "$stock"},
    minStock: {$min: "$stock"}
  }},
  {$sort: {count: -1}}
])

// A6 按借阅年份分组，格式化为 "2024年"
db.borrow_logs.aggregate([
  {$group: {
    _id: {$dateToString: {format: "%Y年", date: "$borrow_date"}},
    count: {$sum: 1}
  }},
  {$sort: {_id: 1}}
])

// A8 关联读者与借阅流水，产出学院借阅量排行（$lookup）
db.borrow_logs.aggregate([
  {$group: {_id: "$reader_card", n: {$sum: 1}}},
  {$lookup: {from: "readers", localField: "_id", foreignField: "card_no", as: "r"}},
  {$unwind: "$r"},
  {$group: {_id: "$r.college", total: {$sum: "$n"}, readers: {$sum: 1}}},
  {$sort: {total: -1}}
])
```

### 索引性能对比

```javascript
// 走索引
db.books.find({category: "计算机"}).explain("executionStats")

// 强制全表扫描
db.books.find({category: "计算机"}).hint({$natural: 1}).explain("executionStats")
```

| 项目 | 走索引 | 全表扫描 |
|---|---|---|
| `winningPlan.stage` | `FETCH`（走 IXSCAN） | `COLLSCAN` |
| `totalDocsExamined` | **7** | **20** |
| `totalKeysExamined` | 7 | 0 |

> 数据量小时耗时差异不明显，用 `totalDocsExamined` 作为索引效果的量化证据。

---

## 常见问题

### 连不上数据库

```text
ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused
```

检查 mongod 是否在跑：

```bash
ss -lntp | grep 27017
```

### 认证失败

```text
pymongo.errors.OperationFailure: Authentication failed.
```

三个常见原因：

1. 密码没有 URL 编码 —— `Lab@2026` 要写成 `Lab%402026`
2. `authSource` 写错 —— 业务账号建在 `library` 库，填 `library` 不是 `admin`
3. 用户名拼错（大小写敏感）

### 时间序列插入报错

```text
timeField 'borrow_date' must be a Date
```

`{"$date": "..."}` 没有还原成 `datetime`。确认用的是 `bson.json_util.loads()`。

### 视图写入报错

```text
CommandNotSupportedOnView: Cannot write to namespace library.book_in_stock
```

视图是只读的，写数据要往 `books` 集合写。这是正常现象，不是 bug。

### 唯一索引冲突

```text
E11000 duplicate key error collection: library.books index: isbn_unique
```

ISBN 重复。换一个不重复的 ISBN，或先删除旧文档。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源，可自由用于学习与二次开发。
数据集为虚构演示数据，不涉及真实借阅信息。
