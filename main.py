# 主程序文件
from file import FileManager
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, make_response, send_file, send_from_directory,flash,Response
from flask_socketio import SocketIO, send, emit
from db_controller import UserManager #用于控制用户数据库
import secrets
import datetime
from PIL import Image
import io
import base64
import requests
import functools


app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = secrets.token_hex(32)

def login_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' in session:  # 登录后将会话中设置了'username'作为登录标识
            return func(*args, **kwargs)
        else:
            return render_template('error/401.html'), 401
    return wrapper

# 自定义错误页面处理示例
@app.errorhandler(404)  
def page_not_found(error):  
    return render_template('error/404.html'), 404  
  
@app.errorhandler(500)  
def server_error(error):  
    return render_template('error/500.html'), 500  
  
@app.errorhandler(403)  
def forbidden(error):  
    return render_template('error/403.html'), 403  
  
@app.errorhandler(405)  
def method_not_allowed(error):  
    return render_template('error/405.html'), 405

@app.errorhandler(401)  
def no_login(error):  
    return render_template('error/401.html'), 401

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

@app.route('/api')
def api():
    return render_template('api.html')
	
@app.route('/api/avatar/<username>', methods=['GET'])
def avatar(username):
    # 创建 UserManager 实例
    user_manager = UserManager()
    if not username:
        return jsonify({"error": "Username is required"}), 400
    
    # 使用 UserManager 获取头像数据（Base64编码）
    avatar_base64 = user_manager.get_avatar(username)
    
    if avatar_base64:
        # 如果成功获取头像，返回一个 data:image URL
        avatar_url = f"{avatar_base64}"
        return jsonify({"avatar_base64": avatar_url})
    else:
        # 如果头像没有找到或出错，返回错误信息
        return jsonify({"error": "Avatar not found"})


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
        session['username'] = result[4]  #  result[4] 是用户名
        flash('登录成功！')
        return redirect(url_for('index'))  # 登录成功后跳转到主页面
    else:
        # 登录失败，显示错误消息
        # 如果 result 是字典，则应使用 result.get('error', '用户名或密码错误')
        error_message = result.get('error', '用户名或密码错误') if isinstance(result, dict) else '用户名或密码错误'
        flash(error_message, '用户名或密码错误,请检查你的用户名或密码,注意区分大小写')
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
            # 注册成功后，自动登录
            client_ip = request.remote_addr
            if not client_ip:
                client_ip = "255.255.255.255"  # 默认 IP 地址

            # 调用 login_user 进行自动登录
            success_login, result = user_manager.login_user(username, password, client_ip)
            if success_login:
                # 登录成功后，设置 session
                session['username'] = result[4]  # 假设 result[4] 是用户名
                flash('注册并登录成功！')
                return jsonify({"message": "用户注册并登录成功！"}), 201
            else:
                # 登录失败，返回错误
                error_message = result.get('error', '用户名或密码错误') if isinstance(result, dict) else '用户名或密码错误'
                return jsonify({"error": error_message}), 401

        else:
            return jsonify({"error": "用户名已存在或注册失败，请稍后再试。"}), 409
    except Exception as e:
        # 记录详细的异常信息
        app.logger.error(f"注册过程中发生错误: {str(e)}")
        # 返回服务器错误响应，并包含可能的错误信息
        return jsonify({"error": "注册过程中发生错误，请稍后再试。服务器已记录详细信息。"}), 500

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user_manager = UserManager()
    if request.method == 'GET':
        return render_template('changepassword.html')
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = session.get('username')
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not username or not old_password or not new_password:
            return jsonify({"error": "Missing required fields"}), 400

        # 获取用户信息
        user_info = user_manager.get_user_info(username)
        if not user_info:
            return jsonify({"error": "User not found"}), 404

        # 调用UserManager的change_password方法
        success = user_manager.change_password(username, old_password, new_password)

        if not success:
            return jsonify({"error": "Password change failed"}), 400

        # 如果密码修改成功，显示成功消息
        flash("Password changed successfully!")
        return jsonify({"message": "Password changed successfully"}), 200


    
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
	
@app.route('/file', methods=['GET'])
@login_required
def file():
    """文件上传与管理的处理，使用filemanager类"""
    username = session.get('username')
    user_manager = UserManager()
    avatar = user_manager.get_avatar(username)
    return render_template('file.html',avatar=avatar,username=username)

@app.route('/file/upload', methods=['POST'])
def upload_file():
    try:
        # 获取用户的用户名（可以从请求的头部、表单或 Cookie 中获取）
        username = session.get('username')
        if not username:
            return jsonify({"error": "用户未登录或用户名不存在"}), 400

        # 获取上传的文件
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "没有文件上传"}), 400
        
        # 获取文件名
        file_name = file.filename
        if not file_name:
            return jsonify({"error": "文件名不能为空"}), 400

        # 调用文件上传处理函数
        file_manager = FileManager()
        result = file_manager.upload_file(username, file, file_name)

        # 返回成功结果
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/file_download', methods=['GET'])
def download_file_route():
    username = session.get('username')
    if not username:
        return jsonify({"error": "用户未登录或用户名不存在"}), 400
    file_id = request.args.get('file_id')  # 从请求的参数中获取文件id
    code = request.args.get('code')  # 获取验证码（如果文件需要验证的话，该参数可为None）
    file_manager = FileManager()  # 实例化FileManager类
    try:
        if file_id is None:
            raise ValueError("没有指定文件，无法下载")
        file_path = file_manager.download_file(int(file_id), code,username)  # 调用FileManager的download_file方法获取文件路径
        return send_file(file_path, as_attachment=True)  # 使用send_file函数将文件发送给客户端实现下载
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400  # 参数错误返回400状态码
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # 其他异常返回500状态码
    
@app.route('/api/file_list', methods=['GET'])
def list_user_files_route():
    username = session.get('username')
    if not username:
        return jsonify({"error": "用户未登录"}), 401

    # 创建 FileManager 实例
    file_manager = FileManager()
    try:
        files = file_manager.list_user_files(username)
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/file_delete', methods=['DELETE'])
def delete_file_route():
    """
    处理删除文件的路由逻辑，接收文件id作为参数，调用FileManager的delete_file方法来删除文件
    """
    username = session.get('username')
    file_id = request.args.get('file_id')
    if file_id is None:
        return jsonify({"error": "文件id参数不能为空"}), 400
    try:
        file_id = int(file_id)
        file_manager = FileManager()
        file_manager.delete_file(file_id)
        return jsonify({"message": "文件删除成功"}), 200
    except ValueError:
        return jsonify({"error": "文件id格式不正确"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/file_share', methods=['POST'])
@login_required
def file_share_route():
    """
    处理文件分享的路由逻辑，接收文件id和用户名（从已登录的会话中获取），
    调用FileManager的share_file方法来进行文件分享相关操作，
    根据操作结果返回相应的响应信息给前端。
    """
    data = request.get_json()
    file_id = data.get('file_id')
    username = session.get('username')  # 从已登录的会话中获取用户名

    print(data)

    if not file_id:
        return jsonify({"error": "文件id参数不能为空"}), 400

    if not username:
        return jsonify({"error": "用户未登录"}), 401

    # 验证文件id是否为正整数
    try:
        file_id = int(file_id)
        if file_id <= 0:
            return jsonify({"error": "文件id必须是一个正整数"}), 400
    except ValueError:
        return jsonify({"error": "文件id格式不正确"}), 400

    try:
        file_manager = FileManager()
        success, result = file_manager.share_file(file_id, username)
        if success:
            return jsonify({"success": True, "data": result}), 200
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        # 在日志中记录错误详情
        print(f"文件分享操作失败: {e}")
        return jsonify({"error": f"文件分享操作出现未知错误: {e}"}), 500


@app.route('/logout', methods=['GET'])
def logout():
    session.clear()  # 清除session，用户登出
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
        is_banned, last_login_time, user_role,last_login_ip, _ = user_info  # 解包返回的元组
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

@app.route('/api/kanbanniang/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def kanbanniang(subpath):
    # 构建目标 URL，去掉 /api/kanbanniang 前缀，只保留剩余路径
    target_url = f"http://localhost:8080/{subpath}{'?' + request.query_string.decode() if request.query_string else ''}"

    try:
        # 根据不同的 HTTP 方法转发请求
        if request.method == 'GET':
            response = requests.get(target_url, params=request.args, headers=request.headers)
        elif request.method == 'POST':
            response = requests.post(target_url, json=request.json, headers=request.headers)
        elif request.method == 'PUT':
            response = requests.put(target_url, json=request.json, headers=request.headers)
        elif request.method == 'DELETE':
            response = requests.delete(target_url, headers=request.headers)
        elif request.method == 'PATCH':
            response = requests.patch(target_url, json=request.json, headers=request.headers)

        return response.content, response.status_code
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}", 500
    
# 路由: 更新用户头像
@app.route('/update-avatar', methods=['POST'])
def update_avatar_route():
    try:
        # 获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400
        
        # 获取必要的字段
        username = session.get('username')
        new_avatar_base64 = data.get("avatar")
        
        # 验证必要字段是否存在
        if not username or not new_avatar_base64:
            return jsonify({"status": "error", "message": "缺少必要的参数: 'username' 或 'avatar'"}), 400
        
        # 提取图片格式信息和Base64数据
        if new_avatar_base64.startswith("data:image/"):
            header, encoded_image = new_avatar_base64.split(",", 1)
            image_format = header.split(";")[0].split("/")[1]  # 提取图片格式（如 'png' 或 'jpeg'）
        else:
            return jsonify({"status": "error", "message": "无效的Base64数据"}), 400

        # 调整头像大小为64x64
        try:
            # 解码base64为图片
            image_data = base64.b64decode(encoded_image)
            image = Image.open(io.BytesIO(image_data))
            
            # 调整图片大小为64x64
            image = image.resize((64, 64))
            
            # 将调整后的图片重新编码为base64
            buffered = io.BytesIO()
            image.save(buffered, format=image_format.upper())  # 使用提取的图片格式保存
            new_avatar_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')  # 编码为base64字符串
            
            # 重新加上前缀（前端已经提供，后端无需修改格式）
            new_avatar_base64 = f"data:image/{image_format};base64," + new_avatar_base64
        
        except Exception as e:
            return jsonify({"status": "error", "message": "头像图片处理失败: " + str(e)}), 400
        
        # 处理头像更新
        user_manager = UserManager()
        result = user_manager.update_avatar(username, new_avatar_base64)
        
        # 如果返回的是成功信息
        if result['status'] == 'success':
            return jsonify(result), 200
        
        # 如果返回的是失败信息，返回错误
        return jsonify(result), 400

    except Exception as e:
        # 捕获未知错误并返回
        return jsonify({"status": "error", "message": f"服务器内部错误: {str(e)}"}), 500
    
@app.route('/game/wuziqi', methods=['GET'])
def game():
    return render_template('wuziqi.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80,debug=True)
