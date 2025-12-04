import os
import json
import sqlite3
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64

# 生成加密密钥的函数
def generate_key():
    # 使用固定盐值，确保每次生成的密钥相同
    salt = b"fixed_salt_for_witch_trial_config_2024"  
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    # 使用固定密码生成密钥
    key = base64.urlsafe_b64encode(kdf.derive(b"witch_trial_cloud_save_secure_key"))
    return key

# 获取用户应用数据目录
def get_app_data_dir():
    app_data_dir = Path.home() / "AppData" / "Local" / "WitchTrialCloudSave"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir

# 默认配置
DEFAULT_CONFIG = {
    "git_platform": "github",  # github
    "github_owner": "",
    "github_repo": "",
    "github_token": "",
    "auto_action": "none",  # none, pull, push
    "save_dir": str(Path.home() / "AppData" / "LocalLow" / "Re,AER" / "manosaba" / "Saves_v1"),
    "backup_interval": 5,  # 监控间隔（秒）
    "notifications_enabled": True,
    "debug_mode": False  # 调试模式开关
}

class Config:
    def __init__(self):
        # 将配置文件存储在用户应用数据目录中
        self.app_data_dir = get_app_data_dir()
        self.config_path = self.app_data_dir / "config.db"
        self.key = generate_key()
        self.cipher_suite = Fernet(self.key)
        self.conn = None
        self.cursor = None
        self.initialize_db()
        self.load()
    
    def initialize_db(self):
        # 连接到SQLite数据库（如果不存在则创建）
        self.conn = sqlite3.connect(str(self.config_path))
        self.cursor = self.conn.cursor()
        
        # 创建配置表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        self.conn.commit()
    
    def encrypt(self, data):
        """加密数据"""
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data, ensure_ascii=False)
        else:
            data_str = str(data)
        return self.cipher_suite.encrypt(data_str.encode()).decode()
    
    def decrypt(self, encrypted_data):
        """解密数据"""
        decrypted_bytes = self.cipher_suite.decrypt(encrypted_data.encode())
        return decrypted_bytes.decode()
    
    def load(self):
        """从数据库加载配置"""
        self.data = DEFAULT_CONFIG.copy()
        
        # 从数据库中读取所有配置
        self.cursor.execute("SELECT key, value FROM config")
        rows = self.cursor.fetchall()
        
        for key, encrypted_value in rows:
            try:
                decrypted_value = self.decrypt(encrypted_value)
                # 尝试解析为JSON，如果失败则作为字符串
                try:
                    self.data[key] = json.loads(decrypted_value)
                except json.JSONDecodeError:
                    # 对于布尔值和整数的特殊处理
                    if decrypted_value.lower() == "true":
                        self.data[key] = True
                    elif decrypted_value.lower() == "false":
                        self.data[key] = False
                    elif decrypted_value.isdigit():
                        self.data[key] = int(decrypted_value)
                    else:
                        self.data[key] = decrypted_value
            except Exception as e:
                print(f"加载配置 {key} 失败: {e}")
                # 使用默认值
                if key in DEFAULT_CONFIG:
                    self.data[key] = DEFAULT_CONFIG[key]
    
    def save(self):
        """保存配置到数据库"""
        # 开启事务
        self.conn.execute("BEGIN TRANSACTION")
        
        try:
            # 保存所有配置项
            for key, value in self.data.items():
                encrypted_value = self.encrypt(value)
                # 使用UPSERT语法，不存在则插入，存在则更新
                self.cursor.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (key, encrypted_value)
                )
            # 提交事务
            self.conn.commit()
        except Exception as e:
            print(f"保存配置失败: {e}")
            # 回滚事务
            self.conn.rollback()
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.data.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.data[key] = value
        self.save()
    
    def __del__(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()