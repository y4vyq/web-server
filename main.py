# 主程序文件

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, make_response, send_file, send_from_directory,flash

from flask_socketio import SocketIO, send, emit
from db_controller import UserManager #用于控制用户数据库
import secrets
import datetime

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = secrets.token_hex(32)

# 在请求之前记录信息的函数，用于记录用户ip
@app.before_request
def log_request_info():
    # 获取IP地址
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()

    # 获取User-Agent字符串
    user_agent = request.headers.get('User-Agent')

@app.route('/robots.txt')   #爬虫用的robots，可要可不要
def robots_txt():
    return send_from_directory(app.static_folder, 'robots.txt')


@app.route('/api/login', methods=['POST'])
def api_login():
    # 获取用户名和密码
    username = request.form.get('username')
    password = request.form.get('password')

    # 创建 UserManager 实例
    user_manager = UserManager()

    # 检查用户名和密码是否为空
    if not username or not password:
        flash('用户名和密码不能为空', 'error')
        return redirect(url_for('login'))

    # 获取客户端 IP 地址
    client_ip = request.remote_addr
    if not client_ip:
        client_ip = "255.255.255.255"  # 默认 IP 地址

    # 调用 UserManager 的 login_user 方法进行登录验证
    success, result = user_manager.login_user(username, password, client_ip)

    # 根据 login_user 的返回结果进行判断
    if success:
        # result 是字典，则应使用 result['username']
        session['username'] = result[3]  # 假设 result[3] 是用户名
        flash('登录成功！')
        return redirect(url_for('index'))  # 登录成功后跳转到主页面
    else:
        # 登录失败，显示错误消息
        # 如果 result 是字典，则应使用 result.get('error', '用户名或密码错误')
        error_message = result.get('error', '用户名或密码错误') if isinstance(result, dict) else '用户名或密码错误'
        flash(error_message, '用户名或密码错误,请检查你的用户名或密码')
        return redirect(url_for('login'))

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()  # 获取JSON格式的数据

    username = data.get('username')
    password = data.get('password')

    # 检查用户名和密码是否为空
    if not username or not password:
        return jsonify({"error": "用户名、邮箱和密码不能为空"}), 400

    # 创建 UserManager 实例
    user_manager = UserManager()

    # 注册用户并处理结果
    try:
        success = user_manager.register_user(username, password)
        if success:
            return jsonify({"message": "用户注册成功！"}), 201
        else:
            return jsonify({"error": "用户名已存在或注册失败，请稍后再试。"}), 409
    except Exception as e:
        # 记录详细的异常信息
        app.logger.error(f"注册过程中发生错误: {str(e)}")
        # 返回服务器错误响应
        return jsonify({"error": "注册过程中发生错误，请稍后再试。服务器已记录详细信息。"}), 5
    
@app.route('/login',methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/register',methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/', methods=['GET'])
def index():
    """主页的处理"""
    username = session.get('username')
    user_manager = UserManager()

    # 从数据库中查询用户头像数据
    avatar_base64 = user_manager.get_avatar(username)

    # 尝试从 X-Forwarded-For 头获取真实 IP 地址
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in user_ip:
        # 如果有多个代理转发的 IP 地址，获取第一个
        user_ip = user_ip.split(',')[0]
    web_name = ''
    return render_template('index.html', user_ip=user_ip, avatar=avatar_base64, web_name=web_name,username=username)

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()  # 清除session
    flash('已注销', '用户已注销，请重新登录')
    return redirect(url_for('login'))
	
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # 个人资料设置
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))  # 如果没有登录，跳转到登录页面

    # 也许login_user 返回的是 (userinfo, result) 结构
    user_manager = UserManager()
    user_info = user_manager.get_user_info(username)
    
    if user_info:
        is_banned, last_login_time, user_role, _ = user_info  # 解包返回的元组
        last_login_ip = "未知的ip地址" 
    else:
        is_banned = False
        last_login_time = "未登录"
        user_role = "未知"
        last_login_ip = "未知"

    avatar_base64 = user_manager.get_avatar(username)
    
    return render_template(
        'profile.html',
        username=username,
        last_login_time=last_login_time,
        last_login_ip=last_login_ip,
        user_role=user_role,
        avatar=avatar_base64
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80,debug=True)
