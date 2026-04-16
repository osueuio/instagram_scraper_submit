import json
import time
import base64
import struct
import hmac
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from instagrapi import Client
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """管理 Instagram 会话的持久化，避免重复登录触发风控"""
    
    def __init__(self, session_file: str = "session.json"):
        self.session_file = Path(session_file)
        self.client: Optional[Client] = None

    def _apply_proxy_if_needed(self, client: Client, proxy: str = ""):
        if proxy:
            normalized_proxy = self._normalize_proxy(proxy)
            client.set_proxy(normalized_proxy)
            logger.info("已启用代理: %s", normalized_proxy)

    def _normalize_proxy(self, proxy: str) -> str:
        """统一代理协议前缀大小写，避免库对协议解析失败。"""
        if "://" not in proxy:
            return proxy
        scheme, rest = proxy.split("://", 1)
        return f"{scheme.lower()}://{rest}"

    def _generate_totp_code(self, secret: str) -> str:
        """基于 IG_TOTP_SECRET 生成 6 位验证码（30 秒窗口）。"""
        normalized_secret = secret.replace(" ", "").upper()
        key = base64.b32decode(normalized_secret)
        counter = int(time.time()) // 30
        counter_bytes = struct.pack(">Q", counter)
        digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        code_int = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(code_int % 1_000_000).zfill(6)

    def _safe_call(self, obj: Any, method_name: str, *args, default=None):
        """调用可能因版本差异不存在的方法，不存在时返回 default。"""
        method = getattr(obj, method_name, None)
        if not callable(method):
            return default
        return method(*args)
    
    def load_session(self, proxy: str = "") -> Optional[Client]:
        """优先从本地恢复会话与设备参数；无效则返回 None。"""
        if not self.session_file.exists():
            logger.info("未找到本地会话文件，需要重新登录")
            return None
        
        try:
            client = Client()
            self._apply_proxy_if_needed(client, proxy)
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # 新版优先：直接恢复完整 settings（最兼容）
            settings = session_data.get('settings', {})
            if settings:
                client.set_settings(settings)
            else:
                # 旧版兜底：按字段恢复（兼容历史 session 文件）
                if 'device_settings' in session_data:
                    client.set_settings(session_data['device_settings'])
                self._safe_call(client, 'set_uuids', session_data.get('uuids', {}))
                self._safe_call(client, 'set_authorization', session_data.get('authorization', {}))
                self._safe_call(client, 'set_device_id', session_data.get('device_id', ''))
                self._safe_call(client, 'set_phone_id', session_data.get('phone_id', ''))
                self._safe_call(client, 'set_uuid', session_data.get('uuid', ''))
                self._safe_call(client, 'set_user_id', session_data.get('user_id', ''))
                self._safe_call(client, 'set_token', session_data.get('token', ''))
            
            try:
                client.get_timeline_feed()
                logger.info("已从本地加载有效会话")
                self.client = client
                return client
            except Exception as e:
                logger.warning(f"本地会话已失效: {e}")
                return None
                
        except Exception as e:
            logger.error(f"加载会话文件失败: {e}")
            return None
    
    def save_session(self, client: Client):
        """保存当前会话到本地"""
        session_data = {
            # 统一保存完整 settings，避免不同版本方法差异导致报错
            'settings': client.get_settings(),
            # 兼容保留：若可获取则写入旧字段，方便历史逻辑读取
            'device_settings': client.get_settings(),
            'uuids': self._safe_call(client, 'get_uuids', default={}),
            'authorization': self._safe_call(client, 'get_authorization', default={}),
            'device_id': getattr(client, 'device_id', ''),
            'phone_id': getattr(client, 'phone_id', ''),
            'uuid': getattr(client, 'uuid', ''),
            'user_id': getattr(client, 'user_id', ''),
            'token': getattr(client, 'token', ''),
        }
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 会话已保存到 {self.session_file}")
    
    def login(
        self,
        username: str,
        password: str,
        device_settings: Dict[str, Any],
        proxy: str = "",
        totp_secret: str = "",
    ) -> Client:
        """执行登录并保存会话"""
        client = Client()
        self._apply_proxy_if_needed(client, proxy)
        
        # 设置设备指纹（关键！降低风控概率）
        client.set_settings(device_settings)
        
        logger.info(f"🔐 正在登录账号: {username}")
        
        for attempt in range(1, 3):
            try:
                verification_code = self._generate_totp_code(totp_secret) if totp_secret else None
                client.login(username, password, verification_code=verification_code)
                self.client = client
                self.save_session(client)
                logger.info("✅ 登录成功，会话已持久化")
                return client

            except Exception as e:
                msg = str(e).lower()
                logger.error("❌ 登录失败(第%s次): %s", attempt, e)

                if "challenge" in msg or "suspicious" in msg:
                    logger.error("⚠️ 账号可能触发风控，请检查邮箱/短信验证")

                if "blacklist" in msg or "change your ip" in msg:
                    logger.error("⚠️ 当前出口 IP 可能被风控，请切换网络或配置 IG_PROXY")
                    raise

                if attempt == 1:
                    logger.info("5 秒后重试登录一次...")
                    time.sleep(5)
                    continue
                raise
    
    def get_client(
        self,
        username: str,
        password: str,
        device_settings: Dict[str, Any],
        proxy: str = "",
        totp_secret: str = "",
    ) -> Client:
        """获取客户端，优先使用本地会话"""
        client = self.load_session(proxy=proxy)
        if client:
            return client

        return self.login(username, password, device_settings, proxy=proxy, totp_secret=totp_secret)