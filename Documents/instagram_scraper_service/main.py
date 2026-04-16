"""Instagram 公开资料抓取（题目核心：登录与会话、列表抓取、随机间隔、导出 JSON）。"""
import sys
import json
import pandas as pd
import logging
from pathlib import Path

from config import config
from session_manager import SessionManager
from scraper import InstagramScraper

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def load_target_users(csv_path: str) -> list:
    """从 CSV 加载目标用户列表，兼容 username 或数字 user_id（pk）。"""
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"找不到输入文件: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # 适配可能的列名变体
    column_mapping = {
        '用户ID': 'identifier',
        '用户名': 'identifier',
        '用户名': 'identifier',
        'username': 'identifier',
        'user_id': 'identifier',
        'User ID': 'identifier',
        'id': 'identifier',
        '用户全名': 'full_name',
        'full_name': 'full_name',
        'Full Name': 'full_name',
        'name': 'full_name',
    }
    
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    if 'identifier' not in df.columns:
        raise ValueError(
            "CSV 缺少目标用户标识列。需要 username 或数字 user_id（pk）列。"
            f" 当前列: {list(df.columns)}"
        )
    
    if 'full_name' not in df.columns:
        df['full_name'] = ''
    
    def _pick_cell_value(value):
        """兼容重复列名时 pandas 返回 Series 的情况。"""
        if isinstance(value, pd.Series):
            for item in value.tolist():
                if not pd.isna(item) and str(item).strip():
                    return item
            return ""
        return value

    users = []
    for _, row in df[['identifier', 'full_name']].iterrows():
        uid = _pick_cell_value(row['identifier'])
        name = _pick_cell_value(row['full_name'])
        users.append({
            'identifier': '' if pd.isna(uid) else str(uid).strip(),
            'full_name': '' if pd.isna(name) else str(name).strip(),
        })
    
    logger.info(f"📋 从 {csv_path} 加载了 {len(users)} 个目标用户")
    return users

def main():
    # 检查环境变量
    if not config.USERNAME or not config.PASSWORD:
        logger.error("❌ 请设置环境变量 IG_USERNAME 和 IG_PASSWORD")
        logger.info("示例: export IG_USERNAME='your_burner_account'")
        sys.exit(1)
    
    # 检查输入文件
    if not Path(config.INPUT_CSV).exists():
        logger.error(f"❌ 找不到输入文件: {config.INPUT_CSV}")
        sys.exit(1)
    
    # 初始化会话管理器
    session_mgr = SessionManager(config.SESSION_FILE)
    
    try:
        # 获取客户端（自动处理会话加载/登录）
        client = session_mgr.get_client(
            config.USERNAME, 
            config.PASSWORD,
            config.DEVICE_SETTINGS,
            config.PROXY,
            config.TOTP_SECRET
        )
        
        # 加载目标用户
        target_users = load_target_users(config.INPUT_CSV)
        if config.MAX_USERS > 0:
            target_users = target_users[:config.MAX_USERS]
            logger.info("🔎 已启用限量抓取: 前 %s 个用户", len(target_users))
        
        # 初始化爬虫
        scraper = InstagramScraper(
            client,
            min_delay=config.MIN_DELAY,
            max_delay=config.MAX_DELAY,
        )
        
        # 执行抓取
        results = scraper.scrape_users(
            target_users,
            output_file=config.OUTPUT_FILE,
            batch_size=config.BATCH_SIZE,
        )
        
        # 保存结果
        scraper.save_results(config.OUTPUT_FILE)
        
        # 统计
        success_count = sum(1 for r in results if r['status'] == 'success')
        logger.info(f"\n📈 抓取完成: {success_count}/{len(results)} 成功")
        
        if success_count < len(results):
            logger.warning("⚠️ 部分用户抓取失败，请检查日志")
        
    except Exception as e:
        logger.error(f"💥 程序异常终止: {e}")
        msg = str(e).lower()
        if "blacklist" in msg or "change your ip" in msg:
            guidance = {
                "reason": "instagram_ip_risk_control",
                "next_steps": [
                    "使用测试小号在邮箱完成安全验证",
                    "切换网络出口 IP（如手机热点）",
                    "或在 .env 配置 IG_PROXY 后重试",
                    "登录成功后复用 session.json，避免频繁重新登录",
                ],
            }
            with open(config.LOGIN_ERROR_FILE, "w", encoding="utf-8") as f:
                json.dump(guidance, f, indent=2, ensure_ascii=False)
            logger.error("已写入风控处理建议文件: %s", config.LOGIN_ERROR_FILE)
        sys.exit(1)

if __name__ == "__main__":
    main()

