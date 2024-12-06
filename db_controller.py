import sqlite3    
import hashlib    
import os    
import logging    
from datetime import datetime, timedelta 
import base64   
    
# 创建日志文件夹    
if not os.path.exists('logs'):    
    os.makedirs('logs')    
    
# 配置日志    
log_filename = f'logs/{datetime.now().strftime("%Y-%m-%d_%H")}.log'    
logging.basicConfig(filename=log_filename, level=logging.ERROR,    
                    format='%(asctime)s - %(levelname)s - %(message)s',encoding='utf-8')    
    
class UserManager:    
    def __init__(self, db_name='web_users.db'):    
        self.db_name = db_name    
        self.create_table()    
    
    def create_table(self):
        """创建用户表格，如果不存在的话。"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        user_role INTEGER DEFAULT 1,
                        is_banned INTEGER DEFAULT 0,
                        ban_reason TEXT,
                        ban_start_time TEXT,
                        ban_end_time TEXT,
                        last_login_time TEXT,
                        last_login_ip TEXT,
                        avatar TEXT DEFAULT 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsEAAA7BAbiRa+0AAABfaVRYdFNuaXBNZXRhZGF0YQAAAAAAeyJjbGlwUG9pbnRzIjpbeyJ4IjowLCJ5IjowfSx7IngiOjEwNCwieSI6MH0seyJ4IjoxMDQsInkiOjk0fSx7IngiOjAsInkiOjk0fV19rQg+WQAAAH1JREFUeF7t0LEBACAMgLDq/z9XB76ALOyc/UbsUq0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUK0GUKmZB1U6BHwxHV6jAAAAAElFTkSuQmCC'  -- 这是一个非常长的base64字符串，用作avatar的默认值
                    )
                ''')
                conn.commit()
        except sqlite3.OperationalError as e:
            logging.error(f"创建表格失败：{e}")
        except sqlite3.Error as e:
            logging.error(f"数据库操作失败：{e}")
    
    def get_user_info(self, username: str) -> tuple:    
        """获取用户信息，包括是否被封禁、最后登录时间和用户权限。"""    
        try:    
            with sqlite3.connect(self.db_name) as conn:    
                cursor = conn.cursor()    
                cursor.execute('SELECT is_banned, last_login_time, user_role FROM users WHERE username = ?', (username,))    
                user_info = cursor.fetchone()    
                if user_info:    
                    return user_info + (username,)  # 返回 (is_banned, last_login_time, user_role, username) 
                return None    
        except sqlite3.Error as e:    
            logging.error(f"获取用户信息失败：{e}")    
            return None    
    
    def hash_password(self, password: str) -> str:    
        """哈希密码。"""    
        return hashlib.sha256(password.encode()).hexdigest()    
    
    def register_user(self, username: str, password: str, user_role: int = 2) -> bool:
        """注册新用户，包括用户权限，并返回一个布尔值来表示注册是否成功。"""
        if self.get_user_info(username):
            logging.warning("用户名已存在！")
            return False  # 用户名已存在时返回 False

        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]

                if user_count == 0:
                    user_role = 3  # 如果为系统注册的第一个用户，角色值为 3（管理员）
                    """角色值介绍：1为访客，2为普通用户，3为管理员用户"""
                password_hash = self.hash_password(password)

                cursor.execute('INSERT INTO users (username, password_hash, user_role) VALUES (?, ?, ?)',
                            (username, password_hash, user_role))
                conn.commit()

                logging.info(f"用户 {username} 注册成功，角色：{user_role}。数据已记入数据库")
                return True  # 如果数据库操作成功，返回 True
        except sqlite3.Error as e:
            logging.error(f"注册失败，原因：{e}")
        return False  # 如果发生异常，返回 False
  
    def login_user(self, username: str, password: str, client_ip: str) -> tuple:
        """用户登录。"""
        if self.authenticate_and_update_login(username, password, client_ip):
            try:
                logging.info(f"用户 {username} 登录成功。")

                # 获取用户信息，包括角色值
                user_info = self.get_user_info(username)
                if user_info:
                    # 返回 (is_banned, last_login_time, user_role, username)
                    return True, user_info  
            except sqlite3.Error as e:
                logging.error(f"登录失败，数据库错误：{e}")
                return False, {"error": f"数据库操作失败: {str(e)}"}
        else:
            return False, {"error": "用户名或密码错误"}

    def authenticate_and_update_login(self, username: str, password: str, client_ip: str) -> bool:
        """验证用户密码，并更新登录时间和登录IP"""
        try:
            # 连接到数据库
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()

                # 查询用户信息
                cursor.execute('SELECT password_hash, last_login_time, last_login_ip FROM users WHERE username = ?', (username,))
                user_info = cursor.fetchone()

                # 如果没有找到用户，返回False
                if not user_info:
                    logging.warning("用户名不存在！")
                    return False

                stored_hash, _, _ = user_info  # 解包密码哈希

                # 验证密码是否正确
                if self.hash_password(password) == stored_hash:
                    # 获取当前时间
                    last_login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # 更新登录时间和登录IP
                    cursor.execute("""
                        UPDATE users 
                        SET last_login_time = ?, last_login_ip = ?
                        WHERE username = ?
                    """, (last_login_time, client_ip, username))
                    conn.commit()

                    logging.info(f"用户 {username} 登录时间和IP更新成功。")
                    return True
                else:
                    logging.warning("密码错误！")
                    return False
        except sqlite3.Error as e:
            logging.error(f"数据库操作失败: {e}")
            return False
  
    def ban_user(self, username: str, reason: str, duration_days: int = 7) -> None:  
        """封禁用户。"""  
        try:  
            with sqlite3.connect(self.db_name) as conn:  
                cursor = conn.cursor()  
                ban_start_time = datetime.now().isoformat()  
                ban_end_time = (datetime.now() + timedelta(days=duration_days)).isoformat()  
                cursor.execute('UPDATE users SET is_banned = 1, ban_reason = ?, ban_start_time = ?, ban_end_time = ? WHERE username = ?',  
                               (reason, ban_start_time, ban_end_time, username))  
                conn.commit()  
                logging.info(f"用户 {username} 被封禁，原因：{reason}，封禁时长：{duration_days}天。")  
        except sqlite3.Error as e:  
            logging.error(f"封禁失败：{e}")  
  
    def unban_user(self, username: str) -> None:  
        """解封用户。"""  
        try:  
            with sqlite3.connect(self.db_name) as conn:  
                cursor = conn.cursor()  
                cursor.execute('UPDATE users SET is_banned = 0, ban_reason = NULL, ban_start_time = NULL, ban_end_time = NULL WHERE username = ?',  
                               (username,))  
                conn.commit()  
                logging.info(f"用户 {username} 解封成功。")  
        except sqlite3.Error as e:  
            logging.error(f"解封失败：{e}")  
  
    def delete_user(self, username: str) -> None:  
        """删除用户。"""  
        if not self.get_user_info(username):  
            logging.warning("用户不存在，无法删除！")  
            return  
        try:  
            with sqlite3.connect(self.db_name) as conn:  
                cursor = conn.cursor()  
                cursor.execute('DELETE FROM users WHERE username = ?', (username,))  
                conn.commit()  
                logging.info(f"用户 {username} 删除成功。")  
        except sqlite3.Error as e:  
            logging.error(f"删除用户失败：{e}")

    def update_avatar(self, username, new_avatar_base64):
        """更新指定用户的头像。"""
        try:
            try:
                decoded_data = base64.b64decode(new_avatar_base64)
                if len(decoded_data) == 0:
                    raise ValueError("错误的数据")
            except (base64.binascii.Error, ValueError) as e:
                logging.error(f"Base64解码失败：{e}")
                return

            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users
                    SET avatar = ?
                    WHERE username = ?
                ''', (new_avatar_base64, username))
                
                if cursor.rowcount == 0:
                    logging.warning(f"未找到用户名为 '{username}' 的用户，头像未更新。")
                    return
                
                conn.commit()
                logging.info(f"用户 '{username}' 的头像更新成功。")
                
        except sqlite3.Error as e:
            logging.error(f"更新头像失败：{e}")
        except Exception as e:
            logging.error(f"未知错误：{e}")

    def get_avatar(self, username):
        """获取指定用户的头像数据（Base64编码）。"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT avatar
                    FROM users
                    WHERE username = ?
                ''', (username,))
                
                result = cursor.fetchone()
                if result:
                    avatar_base64 = result[0]
                    if avatar_base64:
                        logging.info(f"成功获取用户 '{username}' 的头像。")
                        return avatar_base64
                    else:
                        logging.warning(f"用户 '{username}' 没有设置头像。")
                        return None
                else:
                    logging.warning(f"未找到用户名为 '{username}' 的用户。")
                    return None
        except sqlite3.Error as e:
            logging.error(f"获取头像失败：{e}")
            return None
        except Exception as e:
            logging.error(f"未知错误：{e}")
            return None
    # 入口点
if __name__ == "__main__":
    user_manager = UserManager()
    print("UserManager 实例已创建。")
