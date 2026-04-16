import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Instagram 账号配置（使用小号！）
    USERNAME: str = os.getenv("IG_USERNAME", "")
    PASSWORD: str = os.getenv("IG_PASSWORD", "")
    TOTP_SECRET: str = os.getenv("IG_TOTP_SECRET", "")
    
    # 文件路径
    SESSION_FILE: str = "session.json"
    INPUT_CSV: str = "Instagram抓取目标用户列表.csv"
    OUTPUT_FILE: str = "result.json"
    LOGIN_ERROR_FILE: str = "login_error.json"
    
    # 抓取间隔（秒，随机）
    MIN_DELAY: int = 5
    MAX_DELAY: int = 15
    # 仅抓取前 N 个用户（0 表示不限制）
    MAX_USERS: int = int(os.getenv("IG_MAX_USERS", "0"))
    # 每次运行最多新增抓取 N 条（0 表示不限制；配合断点续跑使用）
    BATCH_SIZE: int = int(os.getenv("IG_BATCH_SIZE", "0"))

    # 代理（可选）
    # 示例: http://user:pass@host:port 或 socks5://user:pass@host:port
    PROXY: str = os.getenv("IG_PROXY", "")

    # 设备指纹（与会话一并持久化）
    DEVICE_SETTINGS = {
        "app_version": "312.0.0.34.111",
        "android_version": 30,
        "android_release": "11",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "manufacturer": "Xiaomi",
        "device": "umi",
        "model": "Mi 10",
        "cpu": "qcom",
        "version_code": "543882266"
    }

config = Config()