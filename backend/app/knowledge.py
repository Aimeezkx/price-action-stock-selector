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
        "extraction_status": "rules_indexed",
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
        "extraction_status": "rules_indexed",
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
        "extraction_status": "rules_indexed",
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
        "extraction_status": "rules_indexed",
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
        indexed_rules = sorted(
            rule["id"]
            for rule in RULE_DEFINITIONS
            if any(
                reference["source_id"] == definition["id"]
                for reference in rule["source_references"]
            )
        )
        evidence_pages = sorted(
            {
                page
                for rule in RULE_DEFINITIONS
                for reference in rule["source_references"]
                if reference["source_id"] == definition["id"]
                for page in reference["pages"]
            }
        )
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
                "indexed_rules": indexed_rules,
                "evidence_pages": evidence_pages,
            }
        )
    return sources


def source_reference(
    source_id: str,
    document: str,
    pages: list[int],
    page_basis: str,
    section: str,
    concept: str,
) -> dict:
    return {
        "source_id": source_id,
        "document": document,
        "pages": pages,
        "page_basis": page_basis,
        "section": section,
        "concept": concept,
    }


RULE_DEFINITIONS = [
    {
        "id": "trend_continuation_pullback",
        "name": "趋势延续回踩买点",
        "category": "trend",
        "description": "上升结构中回踩均线/前突破位后，以强势收盘确认趋势延续。",
        "direction": "long",
        "parameters": {"pullback_atr": 0.8, "minimum_rr": 1.8},
        "source_references": [
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [4, 500, 1500],
                "pdf",
                "术语、跟随确认与趋势章节",
                "HH/HL、回调、趋势方向与等待跟随 K 线确认",
            ),
            source_reference(
                "trading_price_action_trends",
                "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
                [252, 269, 278, 336],
                "printed",
                "第18-20章、23章：趋势交易、强度、两段行情与小幅回撤趋势",
                "用趋势强度、两段结构和小幅回撤识别趋势延续",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [4, 500],
                "pdf",
                "突破术语与跟随确认",
                "突破必须结合强势收盘和后续确认",
            ),
            source_reference(
                "trading_price_action_ranges",
                "高级波段技术分析 价格行为交易系统之区间分析(高清).pdf",
                [53, 60, 76, 84],
                "printed",
                "第1-4章：突破案例、突破力度、最初突破和强趋势入场",
                "用突破力度和趋势背景过滤弱突破",
            ),
            source_reference(
                "trading_price_action_trends",
                "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
                [75, 153],
                "printed",
                "第3章突破/测试/反转；第8章收盘价的重要性",
                "突破与收盘位置共同确认趋势进入新阶段",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [500, 2000],
                "pdf",
                "跟随确认、缺口与测量移动",
                "等待回踩确认并用结构距离制定目标",
            ),
            source_reference(
                "trading_price_action_ranges",
                "高级波段技术分析 价格行为交易系统之区间分析(高清).pdf",
                [89, 104],
                "printed",
                "第5-6章：突破失败、突破回调、突破测试与缺口",
                "突破后的回调必须守住关键价位才视为有效测试",
            ),
            source_reference(
                "trading_price_action_reversals_2",
                "高级反转技术分析 价格行为交易系统之反转分析 下  高清.pdf",
                [233],
                "printed",
                "第18章：突破、突破回调及失败突破",
                "区分延续型突破回调与失败突破",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [4, 750],
                "pdf",
                "TTR 术语与交易区间突破",
                "紧密交易区间具有惯性，突破需要扩张确认",
            ),
            source_reference(
                "trading_price_action_ranges",
                "高级波段技术分析 价格行为交易系统之区间分析(高清).pdf",
                [304, 313, 337],
                "printed",
                "第21-23章：区间案例、窄幅交易区间与三角形",
                "将低波动压缩和三角整理程序化为区间突破",
            ),
            source_reference(
                "trading_price_action_trends",
                "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
                [317],
                "printed",
                "第22章：趋势性交易区间",
                "区分趋势中的整理与无方向震荡",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [500, 5000],
                "pdf",
                "信号 K 线、收盘位置与入场触发",
                "长影线拒绝需在关键位出现并以高位收盘确认",
            ),
            source_reference(
                "trading_price_action_trends",
                "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
                [87, 98, 234],
                "printed",
                "第5-6章信号 K 线；第17章摆动点与关键价位",
                "把反转 K 线与水平支撑位置组合，而非孤立识别形态",
            ),
            source_reference(
                "trading_price_action_reversals_1",
                "高级反转技术分析 价格行为交易系统之反转分析 上(高清).pdf",
                [141, 147],
                "printed",
                "第2-3章：反转动能标志与主要趋势反转",
                "影线拒绝必须结合反转动能和结构背景",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [750],
                "pdf",
                "区间惯性与突破尝试",
                "内包压缩代表短期平衡，等待母 K 线边界突破",
            ),
            source_reference(
                "trading_price_action_trends",
                "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
                [98, 143],
                "printed",
                "第6章其他信号 K 线；第7章外包 K 线",
                "以内包/外包关系定义母 K 线压缩和突破边界",
            ),
            source_reference(
                "trading_price_action_ranges",
                "高级波段技术分析 价格行为交易系统之区间分析(高清).pdf",
                [313],
                "printed",
                "第22章：窄幅交易区间",
                "用窄幅区间背景过滤缺乏空间的内包突破",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [4000, 5000],
                "pdf",
                "失望/被困空头与高位收盘",
                "跌破后快速收回支撑代表卖方失败和空头被困",
            ),
            source_reference(
                "trading_price_action_ranges",
                "高级波段技术分析 价格行为交易系统之区间分析(高清).pdf",
                [89, 150],
                "printed",
                "第5章突破失败；第9章预期失败反转信号 K 线",
                "交易区间边缘的失败突破比区间中部信号更有意义",
            ),
            source_reference(
                "trading_price_action_reversals_1",
                "高级反转技术分析 价格行为交易系统之反转分析 上(高清).pdf",
                [347],
                "printed",
                "第9章：失败",
                "失败突破后反向收盘可形成反转触发",
            ),
            source_reference(
                "trading_price_action_reversals_2",
                "高级反转技术分析 价格行为交易系统之反转分析 下  高清.pdf",
                [233],
                "printed",
                "第18章：突破、突破回调及失败突破",
                "结合前一关键位识别失败突破与重新站回",
            ),
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
            source_reference(
                "course_slides_5414",
                "视频教程的 课件幻灯片.pdf",
                [500, 2000],
                "pdf",
                "大 K 线风险与测量移动阻力",
                "过度扩张会放大止损距离并降低追价质量",
            ),
            source_reference(
                "trading_price_action_trends",
                "高级趋势技术分析  价格行为交易系统之趋势分析(高清).pdf",
                [61, 153, 269],
                "printed",
                "第2章趋势 K 线/十字星/高潮；第8章收盘；第19章趋势强度",
                "长上影和弱收盘提示买方动能衰减",
            ),
            source_reference(
                "trading_price_action_reversals_1",
                "高级反转技术分析 价格行为交易系统之反转分析 上(高清).pdf",
                [187],
                "printed",
                "第4章：巅峰反转与高潮后的急速反转",
                "高潮或超大 K 线后的拒绝属于追多风险；成交量阈值是实现层附加过滤",
            ),
        ],
    },
]
