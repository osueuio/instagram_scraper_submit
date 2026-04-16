import random
import time
import json
import logging
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict
from instagrapi import Client
from instagrapi.exceptions import UserNotFound, LoginRequired, ChallengeRequired

logger = logging.getLogger(__name__)

@dataclass
class UserData:
    """用户数据结构"""
    user_id: str = ""
    input_identifier: str = ""
    identifier_type: str = ""        # username/user_pk
    username: str = ""               # 目标账号用户名
    full_name: str = ""
    biography: str = ""
    followers_count: int = 0
    following_count: int = 0
    date_joined: str = ""            # Instagram 公开资料中通常不可得
    account_based_in: str = ""       # 从 biography 启发式提取
    former_usernames_count: int = 0  # 公开接口通常不可得
    email: str = ""                  # 公开接口通常不可得
    fields_unavailable: Dict[str, str] = None
    status: str = "pending"         # pending/success/failed

    def __post_init__(self):
        if self.fields_unavailable is None:
            self.fields_unavailable = {}

    def to_dict(self):
        return asdict(self)

class InstagramScraper:
    def __init__(self, client: Client, min_delay: int = 5, max_delay: int = 15):
        self.client = client
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.results: List[Dict] = []
    
    def _random_sleep(self):
        """随机休眠，模拟人类行为"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"⏳ 休眠 {delay:.1f} 秒...")
        time.sleep(delay)
    
    def _extract_location_from_bio(self, bio: str) -> str:
        """从简介中尝试提取位置信息（简单启发式）"""
        # 常见位置标识词
        location_indicators = ["📍", "Location:", "Based in", "From", "Living in", "🇺🇸", "🇬🇧", "🇨🇳", "🇯🇵", "🇰🇷"]
        for indicator in location_indicators:
            if indicator in bio:
                # 简单提取后面的一段文字
                idx = bio.find(indicator)
                if idx != -1:
                    snippet = bio[idx:idx+50].replace(indicator, "").strip()
                    return snippet.split("\n")[0][:30]
        return ""
    
    def _resolve_user_id_and_type(self, identifier: str):
        """
        返回 (user_pk, identifier_type)
        identifier_type: username 或 user_pk
        """
        if identifier.isdigit():
            return int(identifier), "user_pk"
        return self.client.user_id_from_username(identifier), "username"

    def _load_existing_results(self, filename: str) -> List[Dict]:
        """加载历史抓取结果，用于断点续跑。"""
        path = Path(filename)
        if not path.exists():
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                logger.info("检测到历史结果 %s 条，将自动续跑", len(data))
                return data
            logger.warning("历史结果文件格式异常，已忽略并重新开始")
            return []
        except Exception as e:
            logger.warning("读取历史结果失败，已忽略: %s", e)
            return []

    def _save_results_snapshot(self, filename: str):
        """增量写盘，避免中断时丢失已抓结果。"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

    def fetch_user_data(self, identifier: str, full_name_from_csv: str = "") -> UserData:
        """抓取单个用户公开资料，兼容 username 或 user_pk 输入。"""
        data = UserData(input_identifier=identifier, full_name=full_name_from_csv)
        
        try:
            logger.info("正在抓取: %s", identifier)
            user_pk, identifier_type = self._resolve_user_id_and_type(identifier)
            user_info = self.client.user_info(user_pk)
            
            data.user_id = str(user_info.pk)
            data.identifier_type = identifier_type
            data.username = user_info.username or ""
            data.full_name = user_info.full_name or full_name_from_csv
            data.biography = user_info.biography or ""
            data.followers_count = user_info.follower_count or 0
            data.following_count = user_info.following_count or 0
            data.account_based_in = self._extract_location_from_bio(data.biography)

            # 以下字段在公开资料里通常不可得，保留占位并说明原因，便于面试说明。
            data.email = "[Not Publicly Available]"
            data.date_joined = "[Not Publicly Available]"
            data.former_usernames_count = 0
            data.fields_unavailable = {
                "date_joined": "Instagram public profile APIs do not expose exact account creation time.",
                "email": "Email is private account data and not available from public profile APIs.",
                "former_usernames_count": "Historical usernames are not available from public profile APIs."
            }
            data.status = "success"
            
        except UserNotFound:
            logger.error("用户不存在: %s", identifier)
            data.status = "failed - user not found"
            
        except LoginRequired:
            logger.error("登录失效，需重新认证")
            data.status = "failed - login required"
            
        except ChallengeRequired:
            logger.error("账号触发 Challenge 验证")
            data.status = "failed - challenge required"
            
        except Exception as e:
            err_msg = str(e)
            lowered = err_msg.lower()
            if "ufac_www_bloks" in lowered or "challengeresolve" in lowered or "challenge" in lowered:
                logger.error("账号触发风控 challenge，建议先在 App/网页完成验证后再继续")
                data.status = "failed - challenge required"
            else:
                logger.error("抓取 %s 失败: %s", identifier, e)
                data.status = f"failed - {err_msg}"
        
        return data
    
    def scrape_users(
        self,
        user_list: List[Dict[str, str]],
        output_file: str = "result.json",
        batch_size: int = 0,
    ) -> List[Dict]:
        """
        批量抓取用户列表
        user_list: [{"identifier": "...", "full_name": "..."}, ...]
        """
        existing_results = self._load_existing_results(output_file)
        self.results = existing_results
        processed_identifiers = {
            str(item.get("input_identifier", "")).strip()
            for item in existing_results
            if str(item.get("input_identifier", "")).strip()
        }
        total = len(user_list)
        new_processed_count = 0
        
        for idx, user in enumerate(user_list, 1):
            identifier = str(user.get("identifier") or "").strip()
            full_name = str(user.get("full_name") or "").strip()
            if not identifier:
                continue

            if identifier in processed_identifiers:
                logger.info("跳过已抓取用户: %s", identifier)
                continue
            
            logger.info("进度: %s/%s | %s", idx, total, identifier)
            user_data = self.fetch_user_data(identifier, full_name)
            self.results.append(user_data.to_dict())
            processed_identifiers.add(identifier)
            new_processed_count += 1
            self._save_results_snapshot(output_file)

            if batch_size > 0 and new_processed_count >= batch_size:
                logger.info("达到本轮抓取上限 %s 条，已暂停。下次运行将自动续抓。", batch_size)
                break
            
            if user_data.status in ("failed - login required", "failed - challenge required"):
                logger.error("会话不可用，已停止后续抓取")
                break
            
            if idx < total:
                self._random_sleep()
        
        return self.results
    
    def save_results(self, filename: str = "result.json"):
        """保存结果到 JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 结果已保存到 {filename}，共 {len(self.results)} 条记录")