# ===================== 导入模块 ===================== #
from flask import Flask, request, jsonify, render_template  # Flask主框架：用于创建Web服务器、接收请求和返回响应
import requests                                             # 用于向微信API发起HTTP请求（换取openid）
import sqlite3                                              # 轻量级SQLite数据库模块
import urllib3                                              # 控制HTTPS请求的警告（因为使用自签名证书）
from datetime import datetime                               # 获取当前时间，用于记录注册/登录时间
import os                                                   # 文件系统操作（判断文件存在等）
from flask_cors import CORS                                 # 跨域请求支持

app = Flask(__name__, static_folder='image', static_url_path='/image')# 创建Flask应用对象
CORS(app)  # 启用跨域支持，方便前后端分离开发

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WECHAT_APPID = "wxc3531de3f8cb9b73"      # 微信小程序的AppID
WECHAT_SECRET = "49f90fdedeff9a7c0d1fca8b7bcf277e"  # 微信小程序的AppSecret
DB_PATH = "users.db"                     # SQLite数据库文件路径（项目根目录下）

@app.route('/image/<path:filename>')
def serve_image(filename):
    """返回 image 文件夹下的静态资源"""
    return app.send_static_file(filename)

def init_db():
    """初始化SQLite数据库，若表不存在则自动创建"""
    conn = sqlite3.connect(DB_PATH)  # 连接数据库，没有则自动创建
    cursor = conn.cursor()
    # 创建 users 表（存储openid、昵称、头像、时间等）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 用户序号
            openid TEXT UNIQUE,                    -- 用户在微信唯一标识
            nickname TEXT,                         -- 昵称
            avatar_url TEXT,                       -- 头像URL(暂时不可用)
            
            create_time TEXT,                      -- 注册时间
            login_time TEXT                        -- 最近登录时间
        )
    """)
    # 新增收藏表
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
    # 新增排行榜表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            nickname TEXT,
            avatar_url TEXT,
            mode TEXT NOT NULL,
            score INTEGER NOT NULL,
            play_time TEXT,
            UNIQUE(openid, mode)
        )
    """)
    conn.commit()
    conn.close()
    print("(●'◡'●) 数据库初始化完成：users.db")

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
        conn.commit
        conn.close
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
@app.route('/api/get_favorites', methods=['GET', 'POST'])
def get_favorites():
    """获取用户收藏列表 - 兼容多种参数传递方式 (◕‿◕✿)"""
    print("📩 接收到收藏列表请求: method={}, args={}, json={}, form={}".format(
        request.method,
        dict(request.args),
        request.get_json(silent=True) or "No JSON",
        dict(request.form)
    ))
    
    if request.method == 'GET':
        openid = request.args.get('openid')
        print(f"🔍 GET请求提取openid: {openid}")
    else:
        data = request.get_json(silent=True) or request.form
        openid = data.get('openid') if data else None
        print(f"🔍 POST请求提取openid: {openid}, 数据来源: {'JSON' if request.get_json(silent=True) else 'FORM'}")
    
    print(f"🎯 最终解析的openid: {openid}")
    
    if not openid:
        print("❌ 错误：openid参数为空 (；ω；)")
        return jsonify({
            "status": "fail", 
            "msg": "缺少openid参数 (´；ω；｀)",
            "debug_info": {
                "method": request.method,
                "args_keys": list(request.args.keys()),
                "has_json": bool(request.get_json(silent=True)),
                "form_keys": list(request.form.keys())
            }
        }), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT music_id, music_name, music_author, add_time 
        FROM favorites WHERE openid=? ORDER BY add_time DESC
        """, (openid,))
    favorites = cursor.fetchall()
    conn.close()
    
    favorite_list = [
        {
            "music_id": row[0],
            "music_name": row[1],
            "music_author": row[2],
            "add_time": row[3]
        }
        for row in favorites
    ]
    
    print(f"✅ 成功返回收藏列表: 用户 {openid} 共有 {len(favorite_list)} 个收藏 (◕‿◕✿)")
    
    return jsonify({
        "status": "success",
        "favorites": favorite_list,
        "count": len(favorite_list)
    })

@app.route('/api/add_favorite', methods=['POST'])
def add_favorite():
    """添加收藏 (◕‿◕✿)"""
    print("📩 接收到添加收藏请求: json={}, form={}".format(
        request.get_json(silent=True) or "No JSON",
        dict(request.form)
    ))
    
    data = request.get_json(silent=True) or request.form
    openid = data.get('openid')
    music_id = data.get('music_id')
    music_name = data.get('music_name')
    music_author = data.get('music_author')
    
    print(f"🔍 解析参数 - openid: {openid}, music_id: {music_id}, music_name: {music_name}")
    
    if not all([openid, music_id, music_name]):
        missing = []
        if not openid: missing.append("openid")
        if not music_id: missing.append("music_id") 
        if not music_name: missing.append("music_name")
        print(f"❌ 参数不完整，缺少: {missing} (；ω；)")
        return jsonify({
            "status": "fail", 
            "msg": f"参数不完整，缺少: {', '.join(missing)} (´；ω；｀)"
        }), 400
    
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

@app.route('/api/remove_favorite', methods=['POST'])
def remove_favorite():
    """取消收藏 (◕‿◕✿)"""
    print("📩 接收到取消收藏请求: json={}, form={}".format(
        request.get_json(silent=True) or "No JSON",
        dict(request.form)
    ))
    
    data = request.get_json(silent=True) or request.form
    openid = data.get('openid')
    music_id = data.get('music_id')
    
    print(f"🔍 解析参数 - openid: {openid}, music_id: {music_id}")
    
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

# ===================== 排行榜相关接口 ===================== #
@app.route('/api/get_rank', methods=['GET'])
def get_rank():
    """获取排行榜"""
    mode = request.args.get('mode', 'single')
    limit = int(request.args.get('limit', 50))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT openid, nickname, avatar_url, score, play_time 
        FROM leaderboard 
        WHERE mode=? 
        ORDER BY score DESC 
        LIMIT ?
    """, (mode, limit))
    ranks = cursor.fetchall()
    conn.close()
    
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
    
    return jsonify({
        "status": "success",
        "mode": mode,
        "rankList": rank_list
    })

@app.route('/api/upload_rank', methods=['POST'])
def upload_rank():
    """上传排行榜成绩"""
    data = request.get_json()
    openid = data.get('openid')
    nickname = data.get('nickname')
    avatar_url = data.get('avatar_url')
    mode = data.get('mode')
    score = data.get('score')
    
    if not all([openid, mode, score]):
        return jsonify({"status": "fail", "msg": "参数不完整"}), 400
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查是否已有记录
        cursor.execute("SELECT score FROM leaderboard WHERE openid=? AND mode=?", (openid, mode))
        existing = cursor.fetchone()
        
        # 获取当前模式下的最低分
        cursor.execute("SELECT MIN(score) FROM leaderboard WHERE mode=?", (mode,))
        min_score_result = cursor.fetchone()
        min_score = min_score_result[0] if min_score_result and min_score_result[0] is not None else 0
        
        # 获取当前模式下的记录数量
        cursor.execute("SELECT COUNT(*) FROM leaderboard WHERE mode=?", (mode,))
        count = cursor.fetchone()[0]
        
        if existing:
            # 已有记录，只有当新分数更高时才更新
            if score > existing[0]:
                cursor.execute("""
                    UPDATE leaderboard 
                    SET score=?, nickname=?, avatar_url=?, play_time=?
                    WHERE openid=? AND mode=?
                """, (score, nickname, avatar_url, now, openid, mode))
                print(f"(•̀ᴗ•́)و 更新用户 {openid} 在模式 {mode} 下的分数: {existing[0]} -> {score}")
            else:
                print(f"(￣▽￣) 用户 {openid} 的分数 {score} 未超过现有分数 {existing[0]}，不更新")
        else:
            # 新记录，如果榜单未满或分数高于最低分则插入
            if count < 50 or score > min_score:
                # 如果超过50条，删除最低分
                if count >= 50:
                    cursor.execute("""
                        DELETE FROM leaderboard 
                        WHERE id IN (
                            SELECT id FROM leaderboard 
                            WHERE mode=? AND score = ? 
                            ORDER BY play_time ASC 
                            LIMIT 1
                        )
                    """, (mode, min_score))
                    print(f"(╯°□°）╯ 删除模式 {mode} 下的最低分记录: {min_score}")
                
                cursor.execute("""
                    INSERT INTO leaderboard 
                    (openid, nickname, avatar_url, mode, score, play_time) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (openid, nickname, avatar_url, mode, score, now))
                print(f"(≧▽≦)/ 插入用户 {openid} 在模式 {mode} 下的新记录: {score}")
            else:
                print(f"(￣▽￣) 用户 {openid} 的分数 {score} 未达到上榜要求，最低分: {min_score}")
        
        conn.commit()
        return jsonify({"status": "success", "msg": "成绩上传成功"})
    
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