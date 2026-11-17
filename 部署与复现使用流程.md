# 韧城 RenCheng

灾情信息不完整条件下的应急资源调度推演平台。围绕城区应急物资配送，将灾情证据、道路状态、车辆分配、事件重规划及实验复盘组织到同一工作空间。

## 功能

独立账户与登录注册、文字及文件资料导入、Kimi辅助事件提取、道路搜索、三维建筑视图、需求及车辆编辑、四策略调度、运行事件注入、核查回报、方案导出、历史记录和后台实验任务。

核心方法为双时间证据过滤、同源去重、风险加权最短路、优先级车辆分配和路径影响分数核查。CodeArts用于证据状态模块与边界测试开发。

## 快速启动

需要Python 3.12。仓库附有已构建的前端，运行当前版本无需安装Node.js。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8027
```

Linux/macOS：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8027
```

浏览器打开 http://127.0.0.1:8027 。点击创建账号，用户名至少3字符、密码至少10字符。首次启动自动建立本地SQLite数据库；各账户的场景与方案分别保存。

## 配置在线模型

将`config/model.example.json`复制为`config/model.json`，在本机填写`api_key`。模型与地址使用该文件中的`model`、`base_url`。该文件被Git忽略，密钥仅由后端读取。没有模型配置时，可以运行地图、场景、调度、推演和实验；Kimi提取需配置可用账户及网络。

`.env.example`提供可选PostgreSQL、Redis、公开域名配置说明。这些变量需注入启动进程；应用不会自动读取.env。默认SQLite无需外部数据库。

## 按演示复现

1. 新建场景：种子42、需求12、车辆3、扰动强度0.12。
2. 编辑第一个需求：数量6、时限60分钟，保留其他参数并保存新版本。
3. 计算四种策略，选择稳健优先。对应演示结果：完成率与按时满足率75%，里程29.070千米，遇阻7次。
4. 进入动态推演，播放/暂停，将时间定位20分钟，对道路1050511750注入封闭并重规划。
5. 创建核查任务、提交回报，查看新场景与审计记录。
6. 实验复盘读取450次固定实验；可另行创建少量种子的后台实验任务。

## 实验与测试

```powershell
.\.venv\Scripts\python.exe scripts/run_experiments.py
.\.venv\Scripts\python.exe -m pytest tests vendor/codearts -q
```

完整实验包含种子100—129、扰动0.04/0.12/0.24、5种策略，共450次，命令更新data目录中的指标文件。同一个场景内5种策略共享输入；跨扰动组按种子组织配对分析。

| 策略 | 平均按时满足率 |
|---|---:|
| 效率优先 | 34.35% |
| 稳健优先 | 37.04% |
| 均衡方案 | 36.20% |
| 主动核查 | 36.02% |
| 完全信息参考 | 61.39% |

完整信息参考用于离线实验。常规四策略在前端可选。独立运行包已完成18项测试和450次复验，非计算耗时指标逐项一致。计算耗时取决于执行环境。更详细的数据条件及许可证见[数据来源](DATA_SOURCES.md)。

## 二次开发与部署

前端修改需要Node.js（构建版本24）：

```bash
cd frontend
npm ci
npm run build
```

后端自动提供frontend/dist构建文件。API文档位于/api/docs。

容器运行：`docker compose up -d --build`。Compose挂载data与config目录，并将端口绑定到服务器本机；公网部署另配置HTTPS反向代理与PUBLIC_ORIGIN。已有PostgreSQL/Redis适配不包含云资源自动开通，SQLite历史数据需要单独迁移。

使用`python scripts/backup.py`生成数据库一致备份。数据库、备份、工作日志和真实模型配置均不进入Git。测试会产生测试账户，建议在副本运行。

原始OSM重新提取可另安装`osmium`并执行scripts/extract_geography.py；运行现有系统直接读取已提供的GeoJSON。

## 目录

- backend：接口、调度、工作流、存储适配。
- frontend：源码及已构建页面。
- data：地理、事件、来源及实验记录。
- vendor/codearts：证据状态实现与测试。
- scripts：数据处理、实验与备份。
- tests：认证、算法与业务流程测试。

## 许可

项目代码：[MIT](LICENSE)。地理数据库：ODbL 1.0。实验结果：CC BY 4.0。公开资料及第三方依赖遵循各自权利和许可，详见[DATA_SOURCES.md](DATA_SOURCES.md)。
