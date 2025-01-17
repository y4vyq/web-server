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
        except sqlite3.OperationalError as e:  # 更具体的异常类型
            logging.error(f"创建表格失败：{e}")
        except sqlite3.Error as e:  # 捕获其他sqlite3相关的错误
            logging.error(f"数据库操作失败：{e}")
    
    def get_user_info(self, username: str) -> tuple:
        """获取用户信息，包括是否被封禁、最后登录时间、用户权限以及最后登录IP。"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                # 在SQL查询中加入 last_login_ip 字段
                cursor.execute('SELECT is_banned, last_login_time, user_role, last_login_ip FROM users WHERE username = ?', (username,))
                user_info = cursor.fetchone()
                if user_info:
                    logging.debug(f"用户信息：{user_info}")  # 输出用户信息
                    return user_info + (username,)  # 返回 (is_banned, last_login_time, user_role, last_login_ip, username)
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
        if self.authenticate_and_update_login(username, password, client_ip):  # 传递了 client_ip
            try:
                logging.info(f"用户 {username} 登录成功。")

                # 获取用户信息，包括角色值
                user_info = self.get_user_info(username)
                if user_info:
                    # 返回 (is_banned, last_login_time, user_role, username)
                    return True, user_info  # 确保返回的是完整的用户信息
            except sqlite3.Error as e:
                logging.error(f"登录失败，数据库错误：{e}")
                return False, {"error": f"数据库操作失败: {str(e)}"}
        else:
            return False, {"error": "用户名或密码错误"}
        
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """更改用户密码。

        该方法首先验证提供的旧密码是否正确。如果旧密码正确，更新为新密码。
        如果旧密码不正确，或者用户不存在，返回 False。
        如果密码更新成功，返回 True。

        参数:
        - username: 要更改密码的用户的用户名
        - old_password: 用户提供的当前密码，用于验证
        - new_password: 用户希望设置的新密码

        返回:
        - 如果密码更改成功，返回 True；如果失败，返回 False。
        """
        try:
            # 使用 sqlite3 连接数据库，执行 SQL 操作
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()

                # 查询数据库，获取指定用户名的存储密码哈希值
                print(f"正在查询数据库以获取用户 {username} 的密码哈希值...")
                cursor.execute('SELECT password_hash FROM users WHERE username =?', (username,))
                result = cursor.fetchone()

                # 如果找到该用户
                if result:
                    # 提取存储在数据库中的密码哈希值
                    stored_password_hash = result[0]
                    print(f"用户 {username} 的存储密码哈希值为: {stored_password_hash}")

                    # 将旧密码通过 hash_password(self, password: str) 函数进行哈希并对比
                    password = self.hash_password(old_password)
                    print(f"用户提供的旧密码的哈希值为: {password}")

                    # 比较存储的密码哈希和输入的旧密码哈希
                    if stored_password_hash == password:
                        # 如果旧密码正确，生成新密码的哈希值
                        print(f"旧密码正确，正在生成新密码的哈希值...")
                        new_password_hash = self.hash_password(new_password)
                        print(f"新密码的哈希值为: {new_password_hash}")

                        # 更新数据库中的密码哈希值
                        cursor.execute('UPDATE users SET password_hash =? WHERE username =?', (new_password_hash, username))
                        conn.commit()

                        # 记录日志，表明密码更新成功
                        print(f"用户 {username} 的密码已更新。")
                        return True
                    else:
                        # 如果旧密码不正确，记录日志并返回 False
                        print(f"用户 {username} 提供的旧密码错误。")
                        return False
                else:
                    # 如果没有找到该用户，记录日志并返回 False
                    print(f"用户 {username} 不存在。")
                    return False
        except sqlite3.Error as e:
            # 如果发生数据库操作错误，记录日志并返回 False
            print(f"更改密码失败，发生数据库错误: {e}")
            return False
      
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

                stored_hash, _, _ = user_info  # 解包密码哈希，不关心其他字段

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
        # 检查输入是否为空
        if not new_avatar_base64:
            logging.error("无效的头像数据")
            return {"status": "error", "message": "无效的头像数据"}

        try:
            # 检查用户是否存在
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
                if cursor.fetchone()[0] == 0:
                    logging.warning(f"未找到用户名为 '{username}' 的用户。")
                    return {"status": "error", "message": f"未找到用户名为 '{username}' 的用户。"}

                # 更新头像
                cursor.execute('''
                    UPDATE users
                    SET avatar = ?
                    WHERE username = ?
                ''', (new_avatar_base64, username))

                conn.commit()
                logging.info(f"用户 '{username}' 的头像更新成功。")

            return {"status": "success", "message": "头像更新成功"}
        
        except sqlite3.DatabaseError as e:
            logging.error(f"数据库错误: {e}")
            return {"status": "error", "message": "数据库操作失败"}

        except Exception as e:
            logging.error(f"发生未知错误: {e}")
            return {"status": "error", "message": "更新头像时发生错误"}


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