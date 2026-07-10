# Price Action Stock Selector

一个完整、只读、可解释的日线价格行为选股 Web App。后端使用 FastAPI + SQLAlchemy，前端使用 React 18 + TypeScript + Vite，生产开发栈支持 PostgreSQL、Redis/RQ 与 Docker Compose。真实行情通过 IBKR Pro 的 TWS / IB Gateway 拉取；没有 IBKR 时会自动提供可扫描、可画图、可回测的演示日线。

> 仅用于研究与教育，不构成投资建议。项目不会发送订单。

## 已实现

- IBKR 连接状态、只读连接、合约解析、日线历史数据、pacing delay、幂等 upsert
- 7 张核心表：标的、日线、规则、扫描任务、扫描结果、自选列表、回测运行
- 8 条日线规则：趋势回踩、放量突破、突破回踩、紧密区间突破、Pin Bar、Inside Bar、假跌破收回、长上影风险过滤
- 统一信号输出：score、direction、entry、stop、target、R/R、中文解释、图表标注
- Dashboard、Scanner、K 线分析、Rule Library、Backtest 五个页面
- SVG 原生日线蜡烛图、成交量、关键位/区间、entry/stop/target 标注
- 固定持仓天数 + 固定 R 目标 + 结构止损的事件式基础回测
- 课程资料页码引用与规则 DSL：见 [`knowledge/`](knowledge)
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
```

`IBKR_MARKET_DATA_TYPE=3` 表示延迟数据。是否能取得数据取决于账户权限和市场数据订阅。批量同步会逐 ticker 串行执行，并在请求后节流；历史数据保存在本地，避免重复请求。

若标的原先使用演示 K 线，第一次成功取得 IBKR 数据时会先清除该标的的全部 `DEMO` K 线，防止合成交易日与真实交易所日历混在同一序列；其他演示标的不受影响。

macOS Docker 用户需要让 TWS 接受来自 Docker 虚拟机的连接；Compose 已把 `IBKR_HOST` 设置为 `host.docker.internal`。

## API

| 模块 | Endpoint |
|---|---|
| IBKR | `GET /api/market/ibkr/status`, `POST /api/market/ibkr/connect` |
| 标的/数据 | `POST/GET /api/market/symbols`, `POST /api/market/data/sync-daily`, `GET /api/market/data/daily/{symbol}` |
| 扫描 | `POST /api/scanner/jobs`, `GET /api/scanner/jobs/{id}`, `GET /api/scanner/results`, `GET /api/scanner/results/{id}` |
| 规则 | `GET /api/price-action/rules`, `PATCH /api/price-action/rules/{id}`, `POST /api/price-action/rules/{id}/test` |
| 回测 | `POST /api/backtests`, `GET /api/backtests/{id}` |

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
ruff check app tests

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

## 工程结构

```text
backend/
  app/
    price_action/engine.py   # 指标、结构、8 条规则与评分
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
