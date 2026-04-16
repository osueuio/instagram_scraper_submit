# 面试实战测试：Instagram 用户数据抓取微服务

你好！欢迎参加本次实战测试。

考虑到我们团队全面拥抱 **Vibe Coding（AI 辅助编程）**，本次测试**完全允许且鼓励**你使用任何 AI 编程助手（如 Cursor、GitHub Copilot、ChatGPT、Claude 等）。我们不仅看重最终运行的代码，更看重你拆解问题、编写 Prompt 以及排查错误的能力。

**【重要警告】** 
Instagram 对自动化抓取的风控非常严格。**请务必注册并使用一个全新的“小号（Burner Account）”进行测试！绝对不要使用你的个人主账号**，以免触发风控导致账号被封禁。如果测试过程中账号被封，请在报告中记录下来，这也是真实业务中会遇到的情况。

---

##  任务目标

使用 Python 和开源库 `instagrapi`（推荐使用但不限定），编写一个轻量级的数据抓取脚本（或微服务），实现对指定 Instagram 用户公开数据的安全抓取，并将结果结构化保存。

##  具体需求

### 1. 核心功能要求

*   **账号登录与会话保持**：
    *   程序首次运行时，使用账号密码登录 Instagram。
    *   登录成功后，将当前会话（Session/Cookie）和设备参数持久化保存到本地文件（如 `session.json`）。
    *   程序再次运行时，必须优先从本地加载 `session.json`，避免重复触发登录风控。
*   **数据抓取目标**：
    *   给定一个目标用户列表(用户ID, 用户全名)，参见：Instagram抓取目标用户列表.csv文件。
    *   遍历该列表，抓取每个用户的以下公开信息：
        1. 用户 ID (User ID)
        2. 全名 (Full Name)
        3. 个人简介 (Biography)
        4. 粉丝数 (Followers Count)
        5. 关注数 (Following Count)
	6. 账号创建日期(Date joined)
	7. 账号所在地(Account based in)
	8. 曾用名数量(Former usernames)
	9. email地址(Email)

*   **防风控与休眠机制**：
    *   在抓取不同用户的数据之间，必须加入**随机休眠时间**（例如 5 到 15 秒之间），以模拟人类行为，降低被封禁的概率。
*   **数据输出**：
    *   将抓取到的所有数据导出为一个结构化的 `result.json` 或 `result.csv` 文件。

### 2. 进阶加分项（非强制，但能极大提高评价）

*   **API 化**：使用 `FastAPI` 将上述功能包装成一个 HTTP 接口（例如 `GET /api/scrape?username=nasa`）。
*   **代理支持**：在代码中预留配置代理（Proxy）的入口（可通过环境变量 `.env` 读取代理地址并应用到 `instagrapi` 客户端）。
*   **异常处理**：如果遇到账号私密（Private Account）或用户不存在（User Not Found），程序不能崩溃，应记录错误日志并继续抓取下一个。

---

##  提交要求 (Deliverables)

请将以下内容提供一个 GitHub 私有仓库链接提交给我们：

1.  **源代码**：包含所有 Python 代码文件。
2.  **依赖清单**：`requirements.txt` 或 `Pipfile`/`pyproject.toml`。
3.  **抓取结果**：你本地运行成功后生成的 `result.json` 或 `result.csv` 文件。
4.  **README.md（极其重要）**：
    *   说明如何安装依赖和运行你的代码。
    *   **Vibe Coding 记录**：请简要描述你是如何使用 AI 工具完成这个任务的？（例如：“我先让 Cursor 生成了基础的登录代码，然后发现报错 XXX，我通过修改 Prompt / 查阅 instagrapi 文档解决了这个问题...”）。
    *   如果你在开发过程中遇到了 Instagram 的风控（如 Challenge 拦截、封号），请记录你的现象和思考。

祝你好运！期待看到你的作品。