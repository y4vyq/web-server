import os
import hashlib
import random
import string
import sqlite3
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from pathlib import Path
from db_controller import UserManager
import urllib.parse
from werkzeug.utils import secure_filename

class FileManager:
    def __init__(self, db_name="file_manager.db", upload_dir="upload"):
        """初始化文件管理系统，创建数据库连接和游标，确保数据库和上传目录存在"""
        self.db_name = db_name
        self.upload_dir = Path(upload_dir)
        self._init_database()
        self._init_upload_dir()

    def _init_database(self):
        """创建或连接数据库，并创建必要的表结构"""
        if not os.path.exists(self.db_name):
            self.db_connection = sqlite3.connect(self.db_name)
            self.cursor = self.db_connection.cursor()
            self._create_tables()
        else:
            self.db_connection = sqlite3.connect(self.db_name)
            self.cursor = self.db_connection.cursor()

    def _init_upload_dir(self):
        """确保上传目录存在"""
        if not self.upload_dir.exists():
            self.upload_dir.mkdir(parents=True)

    def _create_tables(self):
        """创建用户、文件和验证码相关的数据库表"""
        create_users_table = '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                role INTEGER NOT NULL,
                folder_path TEXT NOT NULL UNIQUE,
                storage_limit INTEGER NOT NULL DEFAULT 1024,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        '''
        create_files_table = '''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_type TEXT NOT NULL,
                virtual_address TEXT UNIQUE NOT NULL,
                md5 TEXT NOT NULL,
                require_verification BOOLEAN DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        '''
        create_verification_codes_table = '''
            CREATE TABLE IF NOT EXISTS verification_codes (
                file_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                expiry TIMESTAMP NOT NULL,
                FOREIGN KEY(file_id) REFERENCES files(id)
            );
        '''
        try:
            self.cursor.execute(create_users_table)
            self.cursor.execute(create_files_table)
            self.cursor.execute(create_verification_codes_table)
            self.db_connection.commit()
        except sqlite3.Error as e:
            self.db_connection.rollback()
            raise Exception(f"数据库表创建失败: {e}")

    def _get_user(self, username):
        """根据用户名从数据库获取用户信息"""
        query = "SELECT * FROM users WHERE username =?"
        self.cursor.execute(query, (username,))
        user = self.cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'role': user[2],
                'folder_path': user[3],
                'storage_limit': user[4],
                'created_at': user[5],
                'updated_at': user[6],
            }
        return None

    def _handle_new_user(self, username):
        """处理新用户注册逻辑，包括从 UserManager 获取信息、插入数据库和创建文件夹"""
        user_manager = UserManager(db_name="web_users.db")
        user_info = user_manager.get_user_info(username)

        if user_info:
            _, _, user_role, _, _ = user_info
            user_role = 3 if user_role == 3 else 0
            user_folder = self._get_user_folder(username)
            user_folder_str = str(user_folder)

            try:
                self.cursor.execute('''
                    INSERT INTO users (username, role, folder_path)
                    VALUES (?,?,?)
                ''', (username, user_role, user_folder_str))
                self.db_connection.commit()
            except sqlite3.Error as e:
                self.db_connection.rollback()
                raise Exception(f"新用户插入数据库失败: {e}")

            user = self._get_user(username)
            if not user:
                raise Exception("插入用户信息后无法获取用户，可能存在数据库问题")

            return user, user_folder
        else:
            raise Exception("从 UserManager 获取用户信息失败，无法继续")

    def _get_user_folder(self, username):
        """获取或创建用户文件夹路径"""
        user = self._get_user(username)
        if user:
            return Path(user['folder_path'])
        else:
            # 对中文用户名进行 URL 编码
            encoded_username = urllib.parse.quote(username, safe='')  
            folder_path = (self.upload_dir / encoded_username).resolve()
            if not folder_path.exists():
                folder_path.mkdir(parents=True)
            return folder_path

    def _generate_md5(self, file_path):
        """计算文件的 MD5 值"""
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _generate_virtual_address(self, user_id, file_name):
        """生成文件的虚拟地址"""
        return f"/user/{user_id}/file/{file_name}"

    def _generate_verification_code(self, length=4):
        """生成指定长度的验证码"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def _get_unique_file_path(self, user_folder, file_name):
        """在用户文件夹内生成唯一文件路径"""
        base_path = user_folder / file_name
        counter = 1
        while os.path.exists(base_path):
            if file_name.suffix:
                base_path = user_folder / (file_name.stem + f"_{counter}" + file_name.suffix)
            else:
                base_path = user_folder / (file_name.name + f"_{counter}")
            counter += 1
        return base_path

    def upload_file(self, username, file, file_name):
        """上传文件的主要逻辑，包括用户处理、文件保存和数据库插入"""
        if not file.filename:
            raise ValueError("文件名不能为空")

        user = self._get_user(username)
        if not user:
            user, user_folder = self._handle_new_user(username)
        else:
            user_folder = self._get_user_folder(username)

        file_path = self._get_unique_file_path(user_folder, Path(file_name))
        try:
            file.save(str(file_path))
            file_size = file.content_length
            file_type = file.content_type
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            file_md5 = self._generate_md5(file_path)
            virtual_address = self._generate_virtual_address(user['id'], file_name)

            self.cursor.execute('''
                INSERT INTO files (user_id, file_name, file_path, file_size, created_at, file_type, virtual_address, md5)
                VALUES (?,?,?,?,?,?,?,?)
            ''', (user['id'], file_name, str(file_path), file_size, created_at, file_type, virtual_address, file_md5))
            self.db_connection.commit()
            file_id = self.cursor.lastrowid
            return {"文件id": file_id, "虚拟地址": virtual_address}
        except sqlite3.Error as e:
            self.db_connection.rollback()
            raise Exception(f"文件上传数据库操作失败: {e}")
        except Exception as e:
            raise Exception(f"文件上传失败: {e}")

    def generate_verification(self, file_id):
        """生成文件验证码并插入数据库"""
        code = self._generate_verification_code()
        current_time = datetime.now()
        expiry_time = current_time + timedelta(minutes=1440)

        try:
            self.cursor.execute('''
                INSERT INTO verification_codes (file_id, code, expiry) VALUES (?,?,?)
            ''', (file_id, code, expiry_time.strftime('%Y-%m-%d %H:%M:%S')))
            self.db_connection.commit()
            return code
        except sqlite3.Error as e:
            self.db_connection.rollback()
            raise Exception(f"验证码生成失败: {e}")

    def verify_code(self, file_id, code):
        """验证文件验证码是否有效"""
        query = "SELECT * FROM verification_codes WHERE file_id =? AND code =? AND expiry > datetime('now')"
        self.cursor.execute(query, (file_id, code))
        record = self.cursor.fetchone()
        return record is not None

    def download_file(self, file_id, code=None, username=None):
        """下载文件逻辑，包括验证码验证和文件路径返回"""
        # 获取文件信息
        file = self._get_file(file_id)
        if file is None:
            raise FileNotFoundError("文件不存在")

        # 如果没有传递用户名，只能通过验证码验证
        if username is None:
            # 文件是否需要验证码验证
            requires_verification = file[10]
            #file[10]为0或1
        
            # 如果文件需要验证码
            if requires_verification:
                if code is None:
                    raise ValueError("文件需要验证码才能下载，请输入验证码。")
                elif not self.verify_code(file_id, code):
                    raise ValueError("验证码错误，请重新输入正确的验证码。")
            # 如果文件不需要验证码，直接返回文件路径
            else:
                return file[3]
    
        else:
            # 获取当前操作的用户信息
            user = self._get_user(username)
            if user is None:
                raise ValueError(f"无法获取用户信息，用户名 '{username}' 不存在。")

            # 获取文件所有者信息
            file_owner = self._get_user_by_file_id(file_id)
            if file_owner is None:
                raise ValueError("无法获取文件所有者信息，文件可能存在异常。")

            # 比对当前用户与文件所有者，若不一致则禁止下载
            print(f"调试：对比所有者")
            if user['username'] != file_owner['username']:
                raise PermissionError("你无权下载该文件，此文件属于其他用户。")

            # 判断文件是否需要验证码验证
            requires_verification = file[10]
            print(f"调试：验证验证码")
            if requires_verification:
                if code is None:
                    raise ValueError("文件需要验证码才能下载，请输入验证码。")
                elif not self.verify_code(file_id, code):
                    raise ValueError("验证码错误，请重新输入正确的验证码。")

        # 如果所有验证都通过，返回文件路径
        return file[3]


    def _get_file(self, file_id):
        """根据文件 ID 从数据库获取文件信息"""
        query = "SELECT * FROM files WHERE id =?"
        self.cursor.execute(query, (file_id,))
        return self.cursor.fetchone()

    def delete_file(self, file_id):
        """删除文件及数据库记录逻辑"""
        file = self._get_file(file_id)
        if file is None:
            raise Exception("文件不存在")

        file_path = Path(file[3])
        if file_path.exists():
            file_path.unlink()

        try:
            self.cursor.execute('''
                DELETE FROM files WHERE id =?
            ''', (file_id,))
            self.db_connection.commit()
        except sqlite3.Error as e:
            self.db_connection.rollback()
            raise Exception(f"删除文件记录失败: {e}")

    def update_file_name(self, file_id, new_name):
        """更新文件名称逻辑，包括文件重命名和数据库更新"""
        file = self._get_file(file_id)
        if file is None:
            raise Exception("文件不存在")

        old_file_path = Path(file[3])
        user_id = file[1]
        user_folder = self._get_user_folder(self._get_user(user_id)['username'])
        file_extension = old_file_path.suffix
        new_file_path = user_folder / (secure_filename(new_name) + file_extension)
        while new_file_path.exists():
            base_name, ext = os.path.splitext(new_name)
            i = 1
            new_name = f"{base_name}_{i}{ext}"
            new_file_path = user_folder / new_name
            i += 1

        try:
            old_file_path.rename(new_file_path)
            self.cursor.execute('''
                UPDATE files
                SET file_name =?, file_path =?, modified_at =?
                WHERE id =?
            ''', (new_name, str(new_file_path), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), file_id))
            self.db_connection.commit()
            return {"file_id": file_id, "new_name": new_name, "new_file_path": str(new_file_path)}
        except (OSError, sqlite3.Error) as e:
            self.db_connection.rollback()
            raise Exception(f"修改文件名失败: {e}")

    def update_user_storage(self, username, new_limit):
        """更新用户存储限制逻辑"""
        user = self._get_user(username)
        if user is None:
            raise Exception("用户不存在")

        try:
            self.cursor.execute('''
                UPDATE users
                SET storage_limit =?, updated_at =?
                WHERE username =?
            ''', (new_limit, datetime.now().strftime('%Y-m-d H:M:S'), username))
            self.db_connection.commit()
            return {"username": username, "new_storage_limit": new_limit}
        except sqlite3.Error as e:
            self.db_connection.rollback()
            raise Exception(f"更新用户存储空间失败: {e}")

    def delete_user(self, username):
        """删除用户及相关文件和数据库记录逻辑"""
        user = self._get_user(username)
        if user is None:
            raise Exception("用户不存在")

        user_id = user['id']
        user_folder = Path(user['folder_path'])

        try:
            files = self._get_files_by_user_id(user_id)
            for file in files:
                file_path = Path(file[3])
                if file_path.exists():
                    file_path.unlink()
                self.cursor.execute('''
                    DELETE FROM files WHERE id =?
                ''', (file[0],))
            self.cursor.execute('''
                DELETE FROM users WHERE id =?
            ''', (user_id,))
            self.db_connection.commit()
            if user_folder.exists():
                user_folder.rmdir()
            return {"username": username, "status": "deleted"}
        except (OSError, sqlite3.Error) as e:
            self.db_connection.rollback()
            raise Exception(f"删除用户失败: {e}")

    def _get_files_by_user_id(self, user_id):
        """根据用户 ID 获取用户的所有文件信息"""
        query = "SELECT * FROM files WHERE user_id =?"
        self.cursor.execute(query, (user_id,))
        return self.cursor.fetchall()
    
    def list_user_files(self, username):
        """列出指定用户的文件信息"""
        user = self._get_user(username)
        if user is None:
            raise Exception("用户不存在或用户没有上传过文件")

        user_id = user['id']
        files = self._get_files_by_user_id(user_id)

        file_list = []
        for file in files:
            file_info = {
                "file_id": file[0],
                "file_name": file[2],
                "file_path": file[3],
                "file_size": file[4],
                "created_at": file[5],
                "modified_at": file[6],
                "file_type": file[7],
                "virtual_address": file[8],
                "md5": file[9],
                "require_verification": file[10]
            }
            file_list.append(file_info)

        return file_list
    
    def _generate_file_virtual_address(self, file):
        """
        根据文件的多个特征（文件名、文件大小、创建时间等）生成一个虚拟地址，通过哈希算法处理后返回。
        这样可以使虚拟地址相对复杂，增强安全性，而不是简单使用文件id暴露信息。
        """
        file_info = f"{file['name']}{file['size']}{file['creation_time']}".encode('utf-8')
        hash_object = hashlib.sha256(file_info)
        return hash_object.hexdigest()

    def share_file(self, file_id, username):
        """
        根据文件相关信息和用户名来决定是否将该文件设置为共享文件，
        如果用户名不是该文件对应的所有者，则返回错误信息，
        如果是所有者，则检查数据库中的verification_codes表是否已有对应文件虚拟地址的记录，
        若有则获取其验证码，若没有则生成新的验证码并插入记录（插入验证码记录到verification_codes表），
        最后生成一个包含文件虚拟地址和验证码的下载地址返回，同时返回生成的验证码。
        """
        if not isinstance(file_id, int):
            return False, "file_id参数类型错误，需要传入整数类型"
        try:
            # 获取文件信息，若文件不存在则返回相应错误
            file = self._get_file(file_id)
            if file is None:
                return False, "文件不存在"

            # 获取文件所有者信息，判断当前用户是否为所有者，不是则返回相应错误
            file_owner = self._get_user_by_file_id(file_id)
            if file_owner['username']!= username:
                return False, "你不是该文件的所有者，无权进行共享操作"

            # 生成文件的虚拟地址
            file_virtual_address = self._generate_file_virtual_address(file)

            # 先查询数据库中是否已存在对应文件虚拟地址的验证码记录
            self.cursor.execute("SELECT code FROM verification_codes WHERE file_virtual_address=?",
                                (file_virtual_address,))
            existing_code = self.cursor.fetchone()

            if existing_code:
                code = existing_code[0]
            else:
                # 生成新的验证码
                code = self._generate_verification_code()
                current_time = datetime.now()
                expiry_time = current_time + timedelta(minutes=1440)

                try:
                    # 插入新的验证码记录到数据库
                    self.cursor.execute('''
                        INSERT INTO verification_codes (file_virtual_address, code, expiry) VALUES (?,?,?)
                    ''', (file_virtual_address, code, expiry_time.strftime('%Y-%m-%d %H:%M:%S')))
                    self.db_connection.commit()
                except sqlite3.Error as e:
                    self.db_connection.rollback()
                    return False, f"设置文件共享失败，验证码生成及插入数据库失败: {e}"

            # 构建下载地址，使用复杂的虚拟地址代替文件id
            download_url = f"/api/file_download?file_virtual_address={file_virtual_address}&code={code}"
            return True, (download_url, code)
        except Exception as e:
            return False, f"共享文件操作出现未知错误: {e}"

    def _get_user_by_file_id(self, file_id):
        """
        根据文件id获取对应的文件所有者信息（通过关联查询获取所属用户信息）
        """
        query = "SELECT users.username, users.id, users.role, users.folder_path, users.storage_limit, users.created_at, users.updated_at " \
                "FROM users " \
                "JOIN files ON users.id = files.user_id " \
                "WHERE files.id =?"
        self.cursor.execute(query, (file_id,))
        user = self.cursor.fetchone()
        if user:
            return {
                'username': user[0],
                'id': user[1],
                'role': user[2],
                'folder_path': user[3],
                'storage_limit': user[4],
                'created_at': user[5],
                'updated_at': user[6],
            }
        return None

    def close(self):
        """关闭数据库连接"""
        self.db_connection.close()