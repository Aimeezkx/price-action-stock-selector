# Price Action Stock Selector

一个完整、只读、可解释的日线价格行为选股 Web App。后端使用 FastAPI + SQLAlchemy，前端使用 React 18 + TypeScript + Vite，生产开发栈支持 PostgreSQL、Redis/RQ 与 Docker Compose。真实行情通过 IBKR Pro 的 TWS / IB Gateway 拉取；没有 IBKR 时会自动提供可扫描、可画图、可回测的演示日线。

> 仅用于研究与教育，不构成投资建议。项目不会发送订单。

## 已实现

- IBKR 连接状态、只读连接、合约解析、日线历史数据、pacing delay、幂等 upsert
- 7 张核心表：标的、日线、规则、扫描任务、扫描结果、自选列表、回测运行
- 12 条日线规则：趋势回踩、放量突破、突破回踩、紧密区间突破、Pin Bar、Inside Bar、假跌破收回、楔形底、双底、H2 二次入场、微型通道回调、长上影风险过滤
- 统一信号输出：score、direction、entry、stop、target、R/R、中文解释、图表标注
- Dashboard、Scanner、K 线分析、Rule Library、Backtest 五个页面
- Scanner 结果按 Score、市值排名排序，Ticker 可直接跳转对应 K 线分析
- TradingView Lightweight Charts 日线蜡烛图、EMA20、成交量、缩放/平移、悬停 OHLC、关键位和交易计划标注
- Scanner 可在 0.5R–10R 设置最低结构 R/R，按“结构目标空间 ÷ 入场止损风险”过滤候选；Backtest 明细可按 Score、市值排名或实际 R 排序
- 固定持仓天数 + 固定 R 目标 + 结构止损的事件式基础回测
- 全部本地资料的 PDF/印刷页码引用与规则 DSL：见 [`knowledge/`](knowledge)
- 5 个本地 PDF 资料源目录（7,226 页），包含趋势、区间与反转上下册；原文件不上传仓库
- S&P 500 自由流通市值权重前 300 股票池，来自 State Street SPY 官方每日持仓
- 美股交易日 `15:00 America/Chicago` 自动同步 IBKR 日线，自动跳过周末和 NYSE 休市日，每只股票只保留最近 300 个交易日
- 可选的美股交易日 `15:30 America/Chicago` 前 20 候选 Gmail 邮件（默认关闭，凭据只从环境变量读取）
- SQLite 零配置启动；PostgreSQL + Redis/RQ Docker 运行

## 快速启动

### Docker（推荐）

```bash
cp .env.example .env
docker compose -f infrastructure/docker-compose.yml up --build
```

- Web App: http://localhost:3000
- API / OpenAPI: http://localhost:8000/docs
- PostgreSQL: localhost:5433
- Redis: localhost:6379

### 本地开发

后端：

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

默认 `SEED_DEMO_DATA=true`。首次启动会生成 6 个演示标的、约 280 个交易日和完整规则库。

### 本地学习资料

规则库页面会读取本机资料源目录并显示文件可用性。默认目录：

```dotenv
PRICE_ACTION_BOOK_ROOT=~/trading/0-阿布价格行为学
PRICE_ACTION_SLIDES_PATH=~/quant trading/priceaction/price-action/resource/视频教程的 课件幻灯片.pdf
```

项目只保存 PDF 的文件名、页数、SHA-256、提取状态和规则引用，不提交或分发原始书籍。5 个资料源均已进入规则 taxonomy：课程使用 PDF 页码，四本书使用人工核对目录后的印刷页码；规则库会显示每个资料源覆盖的规则数与证据页数。

## IBKR 配置

1. 启动 TWS 或 IB Gateway。
2. 在 API 设置中启用 Socket Clients，建议勾选 Read-Only API。
3. Paper TWS 默认端口 `7497`，Live TWS 默认端口 `7496`。
4. 配置环境变量：

```dotenv
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=17
IBKR_READONLY=true
IBKR_MARKET_DATA_TYPE=3
IBKR_REQUEST_DELAY_SECONDS=0.35
MARKET_SYNC_ENABLED=true
MARKET_SYNC_TIMEZONE=America/Chicago
MARKET_SYNC_HOUR=15
MARKET_SYNC_MINUTE=0
MARKET_BAR_RETENTION=300
EMAIL_DIGEST_ENABLED=true
EMAIL_DIGEST_HOUR=15
EMAIL_DIGEST_MINUTE=30
EMAIL_DIGEST_RECIPIENT=zkxaimee0914@gmail.com,foreveraming@gmail.com
EMAIL_SMTP_USERNAME=your-account@gmail.com
EMAIL_SMTP_PASSWORD=your-gmail-app-password
```

`IBKR_MARKET_DATA_TYPE=3` 表示延迟数据。是否能取得数据取决于账户权限和市场数据订阅。批量同步会逐 ticker 串行执行，并在请求后节流；历史数据保存在本地，避免重复请求。

若标的原先使用演示 K 线，第一次成功取得 IBKR 数据时会先清除该标的的全部 `DEMO` K 线，防止合成交易日与真实交易所日历混在同一序列；其他演示标的不受影响。

macOS Docker 用户需要让 TWS 接受来自 Docker 虚拟机的连接；Compose 已把 `IBKR_HOST` 设置为 `host.docker.internal`。

多个收件人使用逗号分隔，例如 `EMAIL_DIGEST_RECIPIENT=zkxaimee0914@gmail.com,foreveraming@gmail.com`。邮件调度只在 `EMAIL_DIGEST_ENABLED=true` 且 Gmail SMTP 用户名和应用专用密码都已配置时运行。不要提交 `.env`；应用专用密码应仅保存在本机或部署平台的 Secret 中。状态和手动触发接口分别为 `GET /api/notifications/email/status` 与 `POST /api/notifications/email/send-digest`。

## S&P 500 Top 300 与自动更新

项目启动时会把 `backend/app/data/sp500_top300.json` 中的 300 个证券加入 `S&P 500 Top 300` watchlist。快照来自 State Street 官方 SPY 每日持仓，按指数权重降序截取；S&P 500 使用自由流通市值加权，因此该权重可作为用户所要求的市值排序口径。当前快照日期为 2026-07-09。

刷新股票池快照：

```bash
cd backend
.venv/bin/python scripts/update_sp500_universe.py
```

自动同步规则：

- 美股实际交易日 15:00（默认 `America/Chicago`）启动，自动跳过周末、Good Friday、Thanksgiving 等 NYSE 休市日；
- 新标的或不足 300 根时请求 2 年日线，随后裁剪到最近 300 个交易日；
- 已完成回填的标的只请求最近 10 天并幂等更新；
- 同步保持串行并沿用 IBKR pacing delay；TWS / IB Gateway 必须在计划时间保持登录；
- `GET /api/market/data/sync-status` 可查看进度、失败数和下一次运行时间；
- `POST /api/market/data/sync-scheduled` 可手动触发同一后台任务。

## API

| 模块 | Endpoint |
|---|---|
| IBKR | `GET /api/market/ibkr/status`, `POST /api/market/ibkr/connect` |
| 标的/数据 | `POST/GET /api/market/symbols`, `POST /api/market/data/sync-daily`, `GET /api/market/data/daily/{symbol}` |
| 股票池/调度 | `GET /api/market/universe/sp500-top300`, `GET /api/market/data/sync-status`, `POST /api/market/data/sync-scheduled` |
| 扫描 | `POST /api/scanner/jobs`, `GET /api/scanner/jobs/{id}`, `GET /api/scanner/results`, `GET /api/scanner/results/{id}` |
| 规则 | `GET /api/price-action/rules`, `PATCH /api/price-action/rules/{id}`, `POST /api/price-action/rules/{id}/test` |
| 资料源 | `GET /api/knowledge/sources` |
| 回测 | `POST /api/backtests`, `GET /api/backtests/{id}` |
| 邮件 | `GET /api/notifications/email/status`, `POST /api/notifications/email/send-digest` |

示例：

```bash
curl -X POST http://localhost:8000/api/scanner/jobs \
  -H 'Content-Type: application/json' \
  -d '{"symbols":["AAPL","NVDA"],"rule_ids":[],"min_score":60}'
```

## 数据库迁移与测试

```bash
cd backend
alembic upgrade head
pytest
ruff check app tests migrations scripts

cd ../frontend
npm run build
```

连接已登录的 TWS 后，可执行只读验收（示例使用 Live TWS 端口；不会发送订单）：

```bash
cd backend
IBKR_PORT=7496 IBKR_CLIENT_ID=191 IBKR_READONLY=true \
  .venv/bin/python scripts/acceptance_ibkr.py --symbol AAPL --duration '1 M'

# 另一个终端启动 API 后，验证同步幂等性、扫描、规则和回测整链路
.venv/bin/python scripts/acceptance_api.py --symbol AAPL
```

GitHub Actions 会自动执行后端 lint/测试/迁移、前端构建与依赖审计，以及前后端容器镜像构建。

## macOS 后台常驻

`infrastructure/macos/com.aimeezkx.price-action-backend.plist` 可将后端注册为用户级 LaunchAgent。服务会在登录后启动并在异常退出时自动重启；网页和终端无需保持打开。配置仍从本地 `backend/.env` 读取。为确保 macOS 重启或重新登录后仍会自动加载，先将 plist 复制到用户的标准 LaunchAgents 目录。

```bash
mkdir -p "$HOME/Library/LaunchAgents"
cp infrastructure/macos/com.aimeezkx.price-action-backend.plist \
  "$HOME/Library/LaunchAgents/com.aimeezkx.price-action-backend.plist"
launchctl load -w "$HOME/Library/LaunchAgents/com.aimeezkx.price-action-backend.plist"
launchctl kickstart -k gui/$(id -u)/com.aimeezkx.price-action-backend
```

状态和日志：

```bash
launchctl print gui/$(id -u)/com.aimeezkx.price-action-backend
tail -f backend/launchd.stderr.log
```

卸载：

```bash
launchctl bootout gui/$(id -u)/com.aimeezkx.price-action-backend
```

LaunchAgent 不能阻止 Mac 睡眠；15:00 行情同步和 15:30 邮件摘要要求 IB Gateway/TWS 已登录、API 端口已打开且电脑处于唤醒状态。使用 Live IB Gateway 时，在 `backend/.env` 设置 `IBKR_PORT=4001`；Live TWS 默认使用 `7496`。

## 工程结构

```text
backend/
  app/
    price_action/engine.py   # 指标、结构、12 条规则与评分
    services/ibkr.py         # TWS / IB Gateway 适配器
    services/scanner.py      # 批量扫描
    services/backtest.py     # 事件式回测
    main.py                  # FastAPI endpoints
  migrations/               # Alembic 初始 schema
  tests/
frontend/
  src/components/            # Layout、KlineChart、ResultTable
  src/pages/                 # 五个核心页面
infrastructure/
  docker-compose.yml
knowledge/
  SOURCE_INDEX.md            # 本地资料索引与页码证据
  rules.yaml                 # 内部规则 DSL
```

## 当前边界

- 第一版只分析日线，不提供分钟线、期权、下单或组合优化。
- 扫描 API 为零配置体验会在请求内执行；`app.worker.run_scan_job` 已提供 RQ 入口，大股票池部署可改为 enqueue。
- 演示数据是确定性合成数据，不能用于评价规则真实收益；真实研究应先通过 IBKR 同步足够长的历史数据。
- 简化回测会等待后续日线触发入场价，再从实际入场日计算持仓期；同一日同时穿越止损和目标时采用保守的止损优先。它仍未建模滑点、手续费、拆股/分红、停牌和幸存者偏差。
- 本次验收环境没有 Docker CLI，因此未实际启动 Compose；CI 会构建两个镜像，但生产前仍应在目标环境验证 Compose 网络、PostgreSQL、Redis/RQ 和 TWS 跨主机连接。Compose 内数据库凭据仅为公开的本地开发默认值。
- 当前前端以生产构建和浏览器 E2E 为主，后端对核心链路有回归测试；后续仍应增加逐规则行为测试和更完整的前端自动化测试。
