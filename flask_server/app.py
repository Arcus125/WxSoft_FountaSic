# ===================== 导入模块 ===================== #
from flask import Flask, request, jsonify, render_template  # Flask主框架：用于创建Web服务器、接收请求和返回响应
import requests                                             # 用于向微信API发起HTTP请求（换取openid）
import sqlite3                                              # 轻量级SQLite数据库模块
import urllib3                                              # 控制HTTPS请求的警告（因为使用自签名证书）
from datetime import datetime                               # 获取当前时间，用于记录注册/登录时间
import os                                                   # 文件系统操作（判断文件存在等）
from flask_cors import CORS                                 # 跨域请求支持
from werkzeug.utils import secure_filename
from flask import send_from_directory

app = Flask(__name__, static_folder='image', static_url_path='/image')# 创建Flask应用对象
CORS(app)  # 启用跨域支持，方便前后端分离开发

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WECHAT_APPID = "wxc3531de3f8cb9b73"      # 微信小程序的AppID
WECHAT_SECRET = "49f90fdedeff9a7c0d1fca8b7bcf277e"  # 微信小程序的AppSecret
DB_PATH = "users.db"                     # SQLite数据库文件路径（项目根目录下）
# 让 /uploads 下的文件可被访问


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

@app.route('/image/<path:filename>')
def serve_image(filename):
    """返回 image 文件夹下的静态资源"""
    return app.send_static_file(filename)

def init_db():
    """初始化SQLite数据库，若表不存在则自动创建，并补齐/升级字段与索引"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # users 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE,
            nickname TEXT,
            avatar_url TEXT,
            create_time TEXT,
            login_time TEXT
        )
    """)

    # favorites 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            music_id INTEGER NOT NULL,
            music_name TEXT NOT NULL,
            music_author TEXT,
            add_time TEXT,
            UNIQUE(openid, music_id)
        )
    """)

    # leaderboard 表（如果不存在则创建，已包含 song_id）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            nickname TEXT,
            avatar_url TEXT,
            song_id TEXT,                -- ✅ 用于按歌曲排行
            score INTEGER NOT NULL,
            play_time TEXT
        )
    """)

    # 兼容已存在的 leaderboard 表，若缺少 song_id 列则补齐
    cursor.execute("PRAGMA table_info(leaderboard)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'song_id' not in cols:
        cursor.execute("ALTER TABLE leaderboard ADD COLUMN song_id TEXT")

    # 创建（若不存在）唯一约束：同一首歌一个用户只保留一条成绩
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_leaderboard_song_user
        ON leaderboard(song_id, openid)
    """)

    # 排行榜查询常用索引：按 song_id、score 排序
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_leaderboard_song_score
        ON leaderboard(song_id, score DESC, play_time ASC)
    """)

    conn.commit()
    conn.close()
    print("(●'◡'●) 数据库初始化/升级完成：users.db")


# ===================== 调用微信API换openid ===================== #
def get_openid_from_wechat(code):
    """调用微信官方接口，通过code换取openid"""
    url = (
        f"https://api.weixin.qq.com/sns/jscode2session?"
        f"appid={WECHAT_APPID}&secret={WECHAT_SECRET}&js_code={code}&grant_type=authorization_code"
    )
    # 向微信服务器发起请求
    resp = requests.get(url)
    return resp.json()  # 返回JSON数据，例如 {"openid": "...", "session_key": "..."}

# ===================== 首页 ===================== #
@app.route('/')
def index():
    """网站首页，返回 text.html 页面"""
    return render_template("text.html")

# ===================== 登录与注册接口 ===================== #
@app.route('/api/login', methods=['POST'])
def api_login():
    """处理微信小程序的登录与注册逻辑"""
    data = request.get_json()  # 从前端POST请求中获取JSON数据
    code = data.get("code")  # 微信登录凭证code
    wx_data = get_openid_from_wechat(code)
    openid = wx_data.get("openid")  # 提取openid
    print("(￣▽￣) 微信返回:", wx_data)

    if not openid:
        return jsonify({"status": "fail", "msg": "微信返回无openid"}), 400

    # 连接数据库，查询是否已有该openid
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nickname, avatar_url FROM users WHERE openid=?", (openid,))
    user = cursor.fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 当前时间
    if user:
        # 已注册 → 更新信息
        cursor.execute(
            "UPDATE users SET login_time=? WHERE openid=?", (now, openid)
        )
        conn.commit()
        conn.close()
        return jsonify({
            "status": "success",
            "openid": openid,
            "nickname": user[1],
            "avatar_url": user[2]
        })
    else:
        return jsonify({
            "status": "fail",
        })

@app.route('/api/upload/image', methods=['POST'])
def api_upload_image():
    f = request.files.get('file')
    if not f:
        return jsonify({'status':'fail','msg':'no file'}), 400

    openid = request.form.get('openid')
    if not openid:
        return jsonify({'status':'fail','msg':'missing openid'}), 400

    # ========== 提取文件后缀名 ==========
    ext = f.filename.rsplit('.', 1)[-1].lower()

    # ========== 重命名: openid.xxx ==========
    filename = secure_filename(f"{openid}.{ext}")

    upload_dir = "./uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    save_path = os.path.join(upload_dir, filename)
    f.save(save_path)

    # 生成可访问地址（根据部署修改）
    public_url = f"http://127.0.0.1:5000/uploads/{filename}"

    # ========== ★ 同步更新数据库中的 avatar_url ==========
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET avatar_url=? WHERE openid=?",
        (public_url, openid)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'status': 'success',
        'filename': filename,
        'avatar_url': public_url
    })

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    code = data.get("code")
    nickname = data.get("nickname", "用户")
    avatar_url = data.get("avatarUrl", "")
    wx_data = get_openid_from_wechat(code)
    openid = wx_data.get("openid")
    if not openid:
        return jsonify({"status": "fail", "msg": "微信返回无openid"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE openid=?", (openid,))
    user = cursor.fetchone()
    if user:  # 已存在
        conn.close()
        return jsonify({"status": "fail", "msg": "用户已注册"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO users (openid, nickname, avatar_url, create_time, login_time) VALUES (?, ?, ?, ?, ?)",
        (openid, nickname, avatar_url, now, now)
    )
    conn.commit()
    conn.close()
    '''
    return jsonify({
        "status": "fail",
    })
    '''
    return jsonify({
        "status": "success",
        "openid": openid,
        "nickname": nickname,
        "avatar_url": avatar_url
    })

# ===================== 删除指定Openid的用户 ===================== #
@app.route('/api/delete_user/<openid>', methods=['DELETE'])
def delete_user(openid):
    """根据 openid 删除用户，并级联删除相关记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favorites WHERE openid=?", (openid,))
    cursor.execute("DELETE FROM leaderboard WHERE openid=?", (openid,))
    cursor.execute("DELETE FROM users WHERE openid=?", (openid,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted:
        return jsonify({"status": "success", "msg": f"用户 openid={openid} 及其相关数据已全部删除"})
    else:
        return jsonify({"status": "fail", "msg": f"未找到 openid={openid} 的用户"})


# ===================== 查询所有用户 ===================== #
@app.route('/api/users', methods=['GET'])
def get_all_users():
    """返回数据库中所有用户的简要信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT openid, nickname, avatar_url FROM users")
    users = cursor.fetchall()
    conn.close()

    # 格式化为简洁字段列表
    user_list = [
        {
            "existUser": 1,
            "openid": row[0],
            "nickname": row[1],
            "avatar_url": row[2],
            "status": "success"
        }
        for row in users
    ]

    return jsonify({
        "status": "success",
        "count": len(user_list),
        "users": user_list
    })

# ===================== 收藏功能相关 ===================== #
@app.route('/api/favorite/get', methods=['POST'])
def get_favorites():
    """根据 openid 返回收藏的 music_id / name / author 数组（三个数组下标对应）"""
    data = request.get_json()
    openid = data.get('openid') if data else None

    if not openid:
        return jsonify({"status": "fail", "msg": "缺少 openid 参数"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT music_id, music_name, music_author FROM favorites WHERE openid=? ORDER BY add_time DESC",
        (openid,)
    )
    rows = cursor.fetchall()
    conn.close()

    # 三个数组下标对应
    fav_ids     = [row[0] for row in rows]
    fav_names   = [row[1] for row in rows]
    fav_authors = [row[2] for row in rows]

    return jsonify({
        "status": "success",
        "fav_ids": fav_ids,
        "fav_names": fav_names,
        "fav_authors": fav_authors,
    })


@app.route('/api/favorite/add', methods=['POST'])
def add_favorite():
    data = request.get_json()
    print("DEBUG /api/favorite/add:", data)
    openid = data.get('openid')
    music_id = data.get('music_id')
    music_name = data.get('music_name')
    music_author = data.get('music_author')
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO favorites 
            (openid, music_id, music_name, music_author, add_time) 
            VALUES (?, ?, ?, ?, ?)
            """, (openid, music_id, music_name, music_author, now))
        conn.commit()
        conn.close()
        print(f"✅ 添加收藏成功: 用户 {openid} 收藏了《{music_name}》 (◕‿◕✿)")
        return jsonify({"status": "success", "msg": "收藏成功 (◕‿◕✿)"})
    except Exception as e:
        conn.close()
        print(f"❌ 添加收藏失败: {str(e)} (；ω；)")
        return jsonify({"status": "fail", "msg": f"数据库错误: {str(e)} (；ω；)"}), 500

@app.route('/api/favorite/remove', methods=['POST'])
def remove_favorite():
    data = request.get_json(silent=True) or request.form
    openid = data.get('openid')
    music_id = data.get('music_id')
    
    if not all([openid, music_id]):
        print("❌ 参数不完整，缺少openid或music_id (；ω；)")
        return jsonify({"status": "fail", "msg": "参数不完整 (´；ω；｀)"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favorites WHERE openid=? AND music_id=?", (openid, music_id))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted:
        print(f"✅ 取消收藏成功: 用户 {openid} 取消了歌曲 {music_id} (´；ω；｀)")
        return jsonify({"status": "success", "msg": "取消收藏成功 (´；ω；｀)"})
    else:
        print(f"⚠️ 取消收藏失败: 未找到用户 {openid} 的歌曲 {music_id} (；ω；)")
        return jsonify({"status": "fail", "msg": "未找到收藏记录 (；ω；)"})
    
@app.route('/debug/favorites')
def debug_fav_grouped():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT openid, music_id, music_name, music_author, add_time FROM favorites ORDER BY openid")
    rows = cursor.fetchall()
    conn.close()

    grouped = {}
    for openid, music_id, music_name, music_author, add_time in rows:
        if openid not in grouped:
            grouped[openid] = []
        grouped[openid].append({
            "music_id": music_id,
            "music_name": music_name,
            "music_author": music_author,
            "add_time": add_time
        })

    # 转为数组形式输出
    result = [
        {"openid": openid, "favorites": favs}
        for openid, favs in grouped.items()
    ]

    return jsonify(result)

# ===================== 排行榜相关接口 ===================== #
@app.route('/debug/leaderboard', methods=['GET'])
def debug_leaderboard():
    """调试用：查看排行榜表全部内容"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, openid, nickname, avatar_url, song_id, score, play_time
        FROM leaderboard
        ORDER BY song_id, score DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # 格式化输出
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "openid": row[1],
            "nickname": row[2],
            "avatar_url": row[3],
            "song_id": row[4],
            "score": row[5],
            "play_time": row[6]
        })

    return jsonify(result)

@app.route('/api/get_rank', methods=['POST'])
def get_rank():
    """获取排行榜（POST），按 song_id 维度；额外返回用户自己的排名/分数"""
    data = request.get_json() or {}
    song_id = data.get('song_id')                 # ✅ 必填
    limit = int(data.get('limit', 50))            # ✅ 前端自定义
    user_openid = data.get('openid')              # 可选：若传则返回用户排名，否则不算

    if not song_id:
        return jsonify({"status": "fail", "msg": "缺少 song_id"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1) 前 N 名
    cursor.execute("""
        SELECT openid, nickname, avatar_url, score, play_time
        FROM leaderboard
        WHERE song_id=?
        ORDER BY score DESC, play_time ASC
        LIMIT ?
    """, (song_id, limit))
    ranks = cursor.fetchall()

    rank_list = []
    for i, row in enumerate(ranks):
        rank_list.append({
            "rank": i + 1,
            "openid": row[0],
            "name": row[1] or "匿名用户",
            "avatar": row[2] or "/image/default_avatar.png",
            "score": row[3],
            "play_time": row[4]
        })

    # 2) 计算用户自己的排名（若提供 openid）
    userRank = None
    userScore = None
    if user_openid:
        # 2.1 查询用户在这首歌下的分数及时间
        cursor.execute("""
            SELECT score, play_time
            FROM leaderboard
            WHERE song_id=? AND openid=?
        """, (song_id, user_openid))
        row = cursor.fetchone()
        if row:
            userScore, userPlayTime = int(row[0]), row[1]

            # 2.2 计算排名（竞争排名法：所有「分数更高」的数量 + 1；同分按时间早的优先）
            #    即 rank = 1 + count(score > userScore) + count(score = userScore and play_time < userPlayTime)
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN score > ? THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN score = ? AND play_time < ? THEN 1 ELSE 0 END)
                FROM leaderboard
                WHERE song_id=?
            """, (userScore, userScore, userPlayTime, song_id))
            higher_or_earlier = cursor.fetchone()[0] or 0
            userRank = int(higher_or_earlier) + 1

    conn.close()

    return jsonify({
        "status": "success",
        "song_id": song_id,
        "limit": limit,
        "rankList": rank_list,
        "userRank": userRank,
        "userScore": userScore
    })

@app.route('/api/upload_rank', methods=['POST'])
def upload_rank():
    """上传排行榜成绩（按 song_id 维度，仅保存更高分）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    nickname = data.get('nickname')
    avatar_url = data.get('avatar_url')
    song_id = data.get('song_id')   # ✅ 必须传
    score = data.get('score')

    if not all([openid, song_id, score]):
        return jsonify({"status": "fail", "msg": "参数不完整（需要 openid、song_id、score）"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 查该用户在该歌曲的现有成绩
        cursor.execute(
            "SELECT score FROM leaderboard WHERE song_id=? AND openid=?",
            (song_id, openid)
        )
        existing = cursor.fetchone()

        if existing:
            # 只有新分数更高才更新
            if int(score) > int(existing[0]):
                cursor.execute("""
                    UPDATE leaderboard
                    SET score=?, nickname=?, avatar_url=?, play_time=?
                    WHERE song_id=? AND openid=?
                """, (int(score), nickname, avatar_url, now, song_id, openid))
                msg = f"分数更新：{existing[0]} -> {score}"
            else:
                msg = "新分数不高于历史记录，忽略"
        else:
            # 首次提交则插入
            cursor.execute("""
                INSERT INTO leaderboard (openid, nickname, avatar_url, song_id, score, play_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (openid, nickname, avatar_url, song_id, int(score), now))
            msg = "首次提交成绩"

        conn.commit()
        return jsonify({"status": "success", "msg": msg})

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "fail", "msg": f"数据库错误: {str(e)}"}), 500
    finally:
        conn.close()
@app.route('/debug/users')
def debug_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

# ===================== 启动服务器 ===================== #
if __name__ == '__main__':
    init_db()  # 启动前确保数据库已创建
    print("(o゜▽゜)o☆ Flask 服务器启动中...")
    app.run(
        host='0.0.0.0',      # 允许局域网访问
        port=5000,           # 监听端口
        debug=True           # 调试模式（代码修改自动重载）
    )