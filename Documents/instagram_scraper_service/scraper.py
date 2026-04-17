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
    identifier_type: str = ""
    username: str = ""
    full_name: str = ""
    biography: str = ""
    followers_count: int = 0
    following_count: int = 0
    date_joined: str = ""
    account_based_in: str = ""
    former_usernames_count: int = 0
    email: str = ""
    fields_unavailable: Dict[str, str] = None
    status: str = "pending"

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
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"⏳ 休眠 {delay:.1f} 秒...")
        time.sleep(delay)

    def _extract_location_from_bio(self, bio: str) -> str:
        indicators = ["📍", "Location:", "Based in", "From", "Living in"]
        if not bio: return ""
        for ind in indicators:
            if ind in bio:
                part = bio[bio.find(ind):].replace(ind,"").strip()
                return part.splitlines()[0][:30]
        return ""

    def _load_existing_results(self, filename: str) -> List[Dict]:
        path = Path(filename)
        if not path.exists():
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # ======================
            # 🔥 关键修复：过滤掉失败的记录，允许重新抓取！
            # ======================
            valid = []
            for item in data:
                # 只保留成功的，失败的丢掉，重新抓
                if item.get("status") == "success":
                    valid.append(item)
            return valid
        except:
            return []

    def _save_results_snapshot(self, filename: str):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

    def fetch_user_data(self, identifier: str, full_name_from_csv: str = "") -> UserData:
        data = UserData(input_identifier=identifier, full_name=full_name_from_csv)
        user_pk = identifier.strip()
        username = full_name_from_csv.strip()

        logger.info(f"【最终解析】ID={user_pk}, 用户名={username}")
        user_info = None

        try:
            # 1. 试ID
            if user_pk and user_pk.isdigit():
                try:
                    user_info = self.client.user_info(user_pk)
                    logger.info(f"✅ ID {user_pk} 抓取成功")
                except Exception:
                    logger.warning(f"❌ ID {user_pk} 失效")

            # 2. 试用户名
            if not user_info and username:
                try:
                    logger.info(f"🔁 尝试用户名: {username}")
                    user_info = self.client.user_info_by_username(username)
                    logger.info(f"✅ 用户名 {username} 抓取成功")
                except Exception as e:
                    logger.error(f"❌ 用户名失败: {e}")

            # 赋值
            if user_info:
                data.user_id = str(user_info.pk)
                data.username = user_info.username
                data.full_name = user_info.full_name
                data.biography = user_info.biography
                data.followers_count = user_info.follower_count
                data.following_count = user_info.following_count
                data.account_based_in = self._extract_location_from_bio(data.biography)
                data.status = "success"
            else:
                data.status = "failed"

        except Exception as e:
            data.status = f"failed: {str(e)}"

        return data

    def scrape_users(self, user_list: List[Dict], output_file="result.json", batch_size=0):
        self.results = self._load_existing_results(output_file)
        processed = {x["input_identifier"].strip() for x in self.results}

        for i, item in enumerate(user_list, 1):
            ident = item.get("identifier", "").strip()
            name = item.get("full_name", "").strip()
            if not ident: continue

            # 已存在 → 跳过
            if ident in processed:
                logger.info(f"✅ 已存在: {ident}")
                continue

            logger.info(f"进度 {i}/{len(user_list)} | {ident} | {name}")
            res = self.fetch_user_data(ident, name)
            self.results.append(res.to_dict())
            self._save_results_snapshot(output_file)
            self._random_sleep()

        return self.results

    def save_results(self, filename="result.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
