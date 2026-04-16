1. 项目功能
账号登录 + 会话持久化（session.json）
批量抓取 Instagram 公开用户数据
支持单个用户 API 抓取
随机间隔防风控
私密账号 / 不存在用户自动跳过
结果导出 result.csv / result.json
支持 HTTP 代理（可选）
完整异常处理与日志

2. 抓取字段
用户 ID (user_id)
用户名 (username)
全名 (full_name)
个人简介 (biography)
粉丝数 (followers_count)
关注数 (following_count)
账号创建日期 (date_joined)
账号所在地 (account_based_in)
曾用名数量 (former_usernames_count)
邮箱 (email)

3.环境安装
用的配置文件requirements.txt
或者pip install instagrapi fastapi uvicorn python-dotenv pandas

4.配置文件（.env）
IG_USERNAME=你的Instagram小号用户名
IG_PASSWORD=你的Instagram密码
IG_TOTP_SECRET=两步验证码密钥（没有就空着）
IG_MAX_USERS=0  # 最多抓多少个用户，0=不限制
IG_BATCH_SIZE=60  # 每批抓60个用户后休息，防封号

5. 运行方式
python main.py

6.启动 API 服务
python api.py

访问接口
http://127.0.0.1:8000/docs

7.输出结果
抓取结果：result.json
会话保存：session.json
错误日志：控制台自动输出

8. Vibe Coding 开发记录（AI 辅助编程过程）
          1.基础框架生成
          我使用 Cursor AI 生成了 instagrapi 登录、会话保存 / 加载的基础代码，快速完成核心登录逻辑。
          2.会话持久化问题修复
          AI 初始生成的代码未正确保存设备信息，导致重复登录触发风控。我通过优化 Prompt，明确要求 “保存完整 session + 设置自定义设备信息”，修复了会话复用失效问题。
          3.数据字段完善
          我向 AI 明确列出 10 个需要抓取的字段，让其生成结构化数据提取逻辑，并补充了 date_joined、former_usernames、based_in 等 Instagram 非直接暴露字段。
          4.防风控逻辑实现
          我提示 AI：“需要在用户之间加入 5–15 秒随机休眠”，快速生成 time.sleep(random.uniform()) 逻辑。
          5.异常处理完善
          针对用户不存在、私密账号、请求限制，我让 AI 补充 try-except 捕获 UserNotFound、PrivateAccount、ChallengeRequired 等异常。
          6.API 包装（FastAPI）
          使用 AI 快速将核心抓取函数封装为 HTTP 接口，实现单用户实时抓取。
          7.数据导出优化
          让 AI 自动生成 CSV/JSON 双格式导出，确保结构化输出可直接用于数据分析。
          8.代理配置
          提示 AI 增加从 .env 读取代理并应用到 instagrapi，完成高可用配置。
          9.运行时报错 'Client' object has no attribute 'get_uuids'，发现是库版本不兼容，旧 API 已废弃。我通过删除不兼容方法，修复了会话保存崩溃问题。
          10.发现原始代码仅在任务结束后统一保存结果，中途中断会丢失数据。我将保存逻辑改为每抓取一个用户就增量写入 result.json，并实现断点续爬，下次运行自动跳过已抓取用户。

整个开发流程90% 使用 AI 辅助完成，核心工作是：
设计任务结构
编写精准 Prompt
排查风控与库报错
整合功能并保证稳定性

9. Instagram 风控与异常记录
      1.Challenge 验证拦截
      现象：登录时返回 ChallengeRequired，要求邮箱 / 短信验证。
      原因：新账号异地登录、频繁登录、无会话保存。
      解决：完成网页验证，保存 session.json，后续直接加载会话即可绕过。
      2.临时请求限制（429 Too Many Requests）
      现象：连续抓取多个用户后抛出 Please wait a few minutes。
      原因：访问频率过高，触发 Instagram 频率限制。
      解决：增加 5–15 秒随机间隔，降低抓取速度。
      3.账号短暂限制登录
      现象：账号被限制操作 10–30 分钟。
      原因：新账号行为异常。
      解决：使用会话登录、降低频率、使用代理（可选）。

风控规避策略总结：
使用全新小号（绝对不使用主号）
必须持久化会话，避免重复登录
用户之间加入随机休眠
不短时间内抓取大量用户
优先抓取公开账号
可使用代理降低 IP 风险

10.项目结构
instagram_scraper_service/
├── .env                                 # 环境变量配置（账号、代理、风控参数）
├── requirements.txt                     # 依赖清单（instagrapi、fastapi 等）
├── README.md                             # 项目说明、运行指南、开发记录
├── main.py                               # 命令行批量抓取脚本
├── api.py                                # FastAPI 接口服务
├── config.py                             # 配置加载与管理
├── session_manager.py                    # Instagram 会话管理（登录、持久化）
├── scraper.py                            # 核心抓取逻辑（数据提取、防风控）
├── Instagram抓取目标用户列表.csv          # 待抓取用户列表
├── session.json                          # 持久化会话文件（避免重复登录风控）
├── result.json                           # 抓取结果文件（支持断点续爬）
├── progress.txt                          # 批量抓取进度记录（防重复抓取）
├── scraper.log                           # 运行日志（调试与问题排查）
└── 面试实战测试：Instagram 用户数据抓取微服务.md  # 任务需求文档
