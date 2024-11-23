# 主程序文件

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, make_response, send_file, send_from_directory,flash

from flask_socketio import SocketIO, send, emit
from db_controller import UserManager #用于控制用户数据库
import secrets
import datetime

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = secrets.token_hex(32)

users = {
    'example_user': 'example_password'  # 用户名: 密码
}

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
        # 假设 result 中包含用户的用户名 (根据你的代码，可能是 result[2])
        # 如果 result 是字典，则应使用 result['username']
        session['username'] = result[2]  # 假设 result[2] 是用户名
        flash('登录成功！', 'success')
        return redirect(url_for('index'))  # 登录成功后跳转到主页面
    else:
        # 登录失败，显示错误消息
        # 如果 result 是字典，则应使用 result.get('error', '用户名或密码错误')
        error_message = result.get('error', '用户名或密码错误') if isinstance(result, dict) else '用户名或密码错误'
        flash(error_message, 'error')
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
        # 返回服务器错误响应，并包含可能的错误信息
        return jsonify({"error": "注册过程中发生错误，请稍后再试。服务器已记录详细信息。"}), 5
    
@app.route('/login',methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/register',methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/',methods=['GET']) #主页
def index():
    """主页的处理,后续编写"""
    # 尝试从 X-Forwarded-For 头获取真实 IP 地址
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip:
        # 可能有多个代理转发的 IP 地址，获取第一个
        user_ip = user_ip.split(',')[0]
    return render_template('index.html', user_ip=user_ip)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80,debug=True)
