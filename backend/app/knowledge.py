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
