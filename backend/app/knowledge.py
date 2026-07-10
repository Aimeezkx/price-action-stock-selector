import os
from pathlib import Path


LOCAL_SOURCE_DEFINITIONS = [
    {
        "id": "course_slides_5414",
        "title": "视频教程的课件幻灯片",
        "filename": "视频教程的 课件幻灯片.pdf",
        "category": "course",
        "pages": 5414,
        "size_bytes": 483056136,
        "sha256": "dfa9e9ba404b2f0779271ac17c6bfe3e5c9cf86fcf1536b9573c0164fc8434a4",
        "extraction_status": "rules_indexed",
        "encryption": "AES-256; printing allowed, copying disabled",
        "path_env": "PRICE_ACTION_SLIDES_PATH",
        "default_path": "~/quant trading/priceaction/price-action/resource/视频教程的 课件幻灯片.pdf",
    },
    {
        "id": "trading_price_action_reversals_1",
        "title": "高级反转技术分析：价格行为交易系统之反转分析（上）",
        "filename": "高级反转技术分析 价格行为交易系统之反转分析 上(高清).pdf",
        "category": "reversal",
        "pages": 417,
        "size_bytes": 135444232,
        "sha256": "bcdec70024a10d1e022d35c4b5976f87273ec7df3365ef41c025749a681f064a",
        "extraction_status": "registered",
        "encryption": "AES; printing and copying disabled",
    },
    {
        "id": "trading_price_action_reversals_2",
        "title": "高级反转技术分析：价格行为交易系统之反转分析（下）",
        "filename": "高级反转技术分析 价格行为交易系统之反转分析 下  高清.pdf",
        "category": "reversal",
        "pages": 498,
        "size_bytes": 157768387,
        "sha256": "2d25f05712edde1382db010ebc78070b47b6aa5dba8d46b602e3af7330a14a2d",
        "extraction_status": "registered",
        "encryption": "none",
    },
    {
        "id": "trading_price_action_ranges",
        "title": "高级波段技术分析：价格行为交易系统之区间分析",
        "filename": "高级波段技术分析 价格行为交易系统之区间分析(高清).pdf",
        "category": "range",
        "pages": 493,
        "size_bytes": 122171290,
        "sha256": "82162b5236a0ce7c83a505fd13d3015b25f546a385ec4bf7fb02f98baa4787de",
        "extraction_status": "registered",
        "encryption": "AES; printing and copying disabled",
    },
    {
        "id": "trading_price_action_trends",
        "title": "高级趋势技术分析：价格行为交易系统之趋势分析",
        "filename": "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
        "category": "trend",
        "pages": 404,
        "size_bytes": 80759177,
        "sha256": "401a66bd8ba0804ab5b3ba81d1da4811cb35021673c0cc07d8e3fc7d30247125",
        "extraction_status": "registered",
        "encryption": "AES; printing and copying disabled",
    },
]


def local_knowledge_sources() -> list[dict]:
    """Return local-only source metadata without redistributing the PDFs."""
    book_root = Path(
        os.getenv("PRICE_ACTION_BOOK_ROOT", "~/trading/0-阿布价格行为学")
    ).expanduser()
    sources = []
    for definition in LOCAL_SOURCE_DEFINITIONS:
        if path_env := definition.get("path_env"):
            path = Path(os.getenv(path_env, definition["default_path"])).expanduser()
        else:
            path = book_root / definition["filename"]
        sources.append(
            {
                **{
                    key: value
                    for key, value in definition.items()
                    if key not in {"path_env", "default_path"}
                },
                "available": path.is_file(),
                "local_path": str(path).replace(str(Path.home()), "~", 1),
                "redistributed": False,
            }
        )
    return sources


RULE_DEFINITIONS = [
    {
        "id": "trend_continuation_pullback",
        "name": "趋势延续回踩买点",
        "category": "trend",
        "description": "上升结构中回踩均线/前突破位后，以强势收盘确认趋势延续。",
        "direction": "long",
        "parameters": {"pullback_atr": 0.8, "minimum_rr": 1.8},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [4, 1500],
                "concept": "HH/HL、趋势与回踩术语",
            },
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [500],
                "concept": "等待跟随 K 线提高确认概率",
            },
        ],
    },
    {
        "id": "resistance_breakout_volume",
        "name": "阻力突破 + 放量确认",
        "category": "breakout",
        "description": "收盘突破过去 40 日阻力，实体和成交量共同确认。",
        "direction": "long",
        "parameters": {"lookback": 40, "volume_ratio": 1.4, "minimum_rr": 2.0},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [4, 500],
                "concept": "突破、跟随与确认",
            }
        ],
    },
    {
        "id": "breakout_pullback_support",
        "name": "突破后回踩支撑确认",
        "category": "breakout",
        "description": "先突破阻力，再回踩但守住突破位，并在高位收盘。",
        "direction": "long",
        "parameters": {"lookback": 40, "retest_days": 10, "tolerance_atr": 0.35},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [500, 2000],
                "concept": "跟随确认与突破测量移动",
            }
        ],
    },
    {
        "id": "tight_range_breakout",
        "name": "窄幅整理后向上突破",
        "category": "compression",
        "description": "低波动紧密交易区间向上扩张，要求强势收盘和成交量确认。",
        "direction": "long",
        "parameters": {"range_days": 7, "compression_ratio": 0.65, "volume_ratio": 1.2},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [4, 750],
                "concept": "TTR 与交易区间突破反复失败",
            }
        ],
    },
    {
        "id": "pin_bar_key_level",
        "name": "Pin Bar 关键位反转",
        "category": "reversal",
        "description": "关键支撑附近出现长下影拒绝，收盘回到 K 线高位。",
        "direction": "long",
        "parameters": {"wick_body_ratio": 2.0, "close_location": 0.65, "lookback": 20},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [500, 5000],
                "concept": "信号 K 线、收盘位置与确认",
            }
        ],
    },
    {
        "id": "inside_bar_breakout",
        "name": "Inside Bar 突破",
        "category": "compression",
        "description": "母 K 线内包压缩后，收盘突破母 K 线高点。",
        "direction": "long",
        "parameters": {"volume_ratio": 1.0, "minimum_rr": 1.8},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [750],
                "concept": "区间惯性与突破尝试",
            }
        ],
    },
    {
        "id": "false_breakdown_reclaim",
        "name": "假跌破后收回支撑",
        "category": "reversal",
        "description": "盘中跌破近期支撑但收盘重新站回，识别被困空头。",
        "direction": "long",
        "parameters": {"lookback": 20, "close_location": 0.6},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [4000, 5000],
                "concept": "失望/被困空头与高位收盘",
            }
        ],
    },
    {
        "id": "high_volume_upper_wick_risk",
        "name": "高位放量长上影风险过滤",
        "category": "risk",
        "description": "上涨后出现放量长上影或超大 K 线，降低追多评分并提示止损距离风险。",
        "direction": "risk",
        "parameters": {"wick_body_ratio": 1.8, "volume_ratio": 1.6, "extended_atr": 2.5},
        "source_references": [
            {
                "document": "视频教程的 课件幻灯片.pdf",
                "pages": [500, 2000],
                "concept": "大 K 线增加风险、测量移动阻力",
            }
        ],
    },
]
