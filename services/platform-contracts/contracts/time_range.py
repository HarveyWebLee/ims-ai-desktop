"""
相对时间 / 自然语言 → 告警查询起止时间（UTC+8 中国标准时间）

文件职责
--------
把「近三天」「昨天到现在」等中文/口语时间解析成告警 API 可用的起止时间字符串；
并提供从整句用户消息抽取时间、给 System Prompt 注入「现在几点」提示等辅助。

白话概念
--------
LLM 常把用户原话塞进 start_time。本模块负责翻译成机器能查库的时间段，
统一用东八区，避免 Windows 缺 tzdata 时 ZoneInfo 崩掉。

在 Agent 流程中的位置
--------------------
  query_alarms / download_file / batch_*
    → resolve_alarm_time_range(...)
  意图短路 / preflight
    → extract_alarm_time_range_from_message（Plan 规则层等只读抽取）
    → enrich_alarm_time_args（历史兼容，已不再回填空槽）
  Prompt 组装
    → format_reference_hint()

对外主入口
----------
  resolve_alarm_time_range(start_time, end_time) → (start_iso, end_iso) 或 None
  format_reference_hint() → 当前时间字符串
  extract_alarm_time_range_from_message / enrich_alarm_time_args

【Python 小白提示】
  - datetime、timedelta：标准库处理日期时间
  - timezone(timedelta(hours=8))：固定东八区
  - re.search：正则；group(1) 取捕获组
"""

from __future__ import annotations

import calendar  # monthrange：某年某月有多少天
import re
from datetime import datetime, timedelta, timezone
from typing import Any

# 固定东八区 CST，避免 Windows 缺 tzdata 时 datetime.now(ZoneInfo) 失败
TZ = timezone(timedelta(hours=8), name="CST")

# 中文数字 → 整数，用于「近三天」「近十二小时」等
_CN_DIGIT = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _now(reference: datetime | None = None) -> datetime:
    """
    得到「带东八区时区」的当前时刻（或指定 reference 转到东八区）。

    参数:
        reference: 可选；测试时可注入固定时间

    返回:
        aware datetime（带 tzinfo），始终在 TZ 时区
    """
    if reference is not None:
        if reference.tzinfo is None:
            # naive datetime：假定已是本地时间，直接贴上 TZ
            return reference.replace(tzinfo=TZ)
        return reference.astimezone(TZ)
    return datetime.now(TZ)


def _start_of_day(dt: datetime) -> datetime:
    """当天 00:00:00.000000"""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(dt: datetime) -> datetime:
    """当天 23:59:59.000000（不含微秒尾数）"""
    return dt.replace(hour=23, minute=59, second=59, microsecond=0)


def _to_iso(dt: datetime) -> str:
    """
    转为 ISO8601 字符串（精确到秒），工具链统一格式。

    例如：2026-07-02T15:30:00+08:00
    """
    return dt.astimezone(TZ).isoformat(timespec="seconds")


def _parse_cn_number(text: str) -> int | None:
    """
    解析简单中文数字或阿拉伯数字字符串。

    支持：5、「五」、十一、二十、二十三 等；无法解析返回 None
    """
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text in _CN_DIGIT:
        return _CN_DIGIT[text]
    # 十一、十二（十 + 个位）
    if len(text) == 2 and text[0] == "十" and text[1] in _CN_DIGIT:
        return 10 + _CN_DIGIT[text[1]]
    # 二十、三十（十位 + 十）
    if len(text) == 2 and text[0] in _CN_DIGIT and text[1] == "十":
        return _CN_DIGIT[text[0]] * 10
    # 二十三（十位 + 十 + 个位）
    if len(text) == 3 and text[1] == "十":
        a, _, b = text[0], text[1], text[2]
        if a in _CN_DIGIT and b in _CN_DIGIT:
            return _CN_DIGIT[a] * 10 + _CN_DIGIT[b]
    return None


def _is_absolute_time(value: str) -> bool:
    """
    判断字符串是否已是「绝对时间」，不需要再走相对语义解析。

    例如：2026-07-01、2026-07-01 12:00:00、ISO8601 带 T 的格式
    """
    v = value.strip()
    if not v:
        return False
    # 含「近、昨天」等相对词且没有 yyyy-mm-dd 的，不算绝对时间
    relative_hints = (
        "近",
        "最近",
        "过去",
        "昨",
        "前",
        "今",
        "本",
        "上",
        "这",
        "个",
    )
    if any(h in v for h in relative_hints) and not re.search(r"\d{4}-\d{2}-\d{2}", v):
        return False
    if re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", v):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}T", v):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(:\d{2})?", v):
        return True
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except ValueError:
        pass
    try:
        datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def _normalize_time_text(text: str) -> str:
    """
    全角数字转半角，避免「近４天」无法被 \\d 匹配。
    str.maketrans + translate 是高效的字符替换方式。
    """
    return text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def _subtract_months(dt: datetime, months: int) -> datetime:
    """
    从 dt 向前推 months 个自然月。

    若原日份在新月不存在（如 3/31 推一月 → 2/28），取该月最后一天。
    """
    year, month = dt.year, dt.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _parse_relative_phrase(text: str, reference: datetime) -> tuple[datetime, datetime] | None:
    """
    从单条相对时间描述解析 (start_datetime, end_datetime)。

    参数:
        text: 如「近三天」「昨天」「近半小时」
        reference: 锚定「现在」的时刻（东八区）

    返回:
        成功则 (start, end)；无法识别则 None
    """
    t = _normalize_time_text(text.strip()).lower()
    if not t:
        return None

    today = _start_of_day(reference)

    if t in ("今天", "今日", "当天"):
        return today, _end_of_day(reference)

    if t in ("昨天", "昨日"):
        d = today - timedelta(days=1)
        return d, _end_of_day(d)

    if t in ("前天",):
        d = today - timedelta(days=2)
        return d, _end_of_day(d)

    if t in ("近一周", "最近一周", "过去一周", "近7天", "最近7天", "过去7天"):
        start = today - timedelta(days=6)
        return start, _end_of_day(reference)

    if re.search(r"近半年|最近半年|过去半年|近6个月|近六个月|最近6个月", t):
        start = _start_of_day(_subtract_months(today, 6))
        return start, _end_of_day(reference)

    if re.search(r"近一年|最近一年|过去一年|近12个月|最近12个月|近12月", t):
        start = _start_of_day(_subtract_months(today, 12))
        return start, _end_of_day(reference)

    if re.search(r"近一个月|最近一个月|过去一个月|近1个月|最近1个月", t):
        start = _start_of_day(_subtract_months(today, 1))
        return start, _end_of_day(reference)

    m_month = re.search(
        r"(?:近|最近|过去)\s*(\d+|[零一二两三四五六七八九十]+)\s*个?\s*月",
        t,
    )
    if m_month:
        n = _parse_cn_number(m_month.group(1))
        if n and n > 0:
            start = _start_of_day(_subtract_months(today, n))
            return start, _end_of_day(reference)

    if t in ("今年", "本年"):
        start = today.replace(month=1, day=1)
        return start, _end_of_day(reference)

    m = re.search(r"(?:近|最近|过去)\s*(\d+|[零一二两三四五六七八九十]+)\s*天", t)
    if m:
        n = _parse_cn_number(m.group(1))
        if n and n > 0:
            # 「近3天」含今天共 3 天：today, today-1, today-2 → start = today-(n-1)
            start = today - timedelta(days=n - 1)
            return start, _end_of_day(reference)

    if re.search(r"近三天|最近三天|过去三天", t):
        start = today - timedelta(days=2)
        return start, _end_of_day(reference)

    m_sec = re.search(
        r"(?:近|最近|过去)\s*(\d+|[零一二两三四五六七八九十]+)\s*秒",
        t,
    )
    if m_sec:
        n = _parse_cn_number(m_sec.group(1))
        if n and n > 0:
            start = reference - timedelta(seconds=n)
            return start, reference

    m_min = re.search(
        r"(?:近|最近|过去)\s*(\d+|[零一二两三四五六七八九十]+)\s*(?:分钟|分)",
        t,
    )
    if m_min:
        n = _parse_cn_number(m_min.group(1))
        if n and n > 0:
            start = reference - timedelta(minutes=n)
            return start, reference

    if re.search(r"近(?:半(?:个)?)?小时|最近(?:半(?:个)?)?小时|过去(?:半(?:个)?)?小时", t):
        start = reference - timedelta(minutes=30)
        return start, reference
    if re.search(r"近半小时|最近半小时|过去半小时", t):
        start = reference - timedelta(minutes=30)
        return start, reference

    m_hour = re.search(
        r"(?:近|最近|过去)\s*(\d+|[零一二两三四五六七八九十]+)\s*小时",
        t,
    )
    if m_hour:
        n = _parse_cn_number(m_hour.group(1))
        if n and n > 0:
            start = reference - timedelta(hours=n)
            return start, reference

    if t in ("本周", "这周", "本星期"):
        weekday = reference.weekday()  # 周一=0
        start = today - timedelta(days=weekday)
        return start, _end_of_day(reference)

    if t in ("上周", "上星期"):
        weekday = reference.weekday()
        end = today - timedelta(days=weekday + 1)
        start = _end_of_day(end) - timedelta(days=6)
        return _start_of_day(start), _end_of_day(end)

    if t in ("本月", "这个月"):
        start = today.replace(day=1)
        return start, _end_of_day(reference)

    if t in ("上月", "上个月"):
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1)
        return start, _end_of_day(last_prev)

    return None


def resolve_alarm_time_range(
    start_time: str = "",
    end_time: str = "",
    *,
    reference: datetime | None = None,
) -> tuple[str, str] | None:
    """
    将 LLM/用户传入的时间字段解析为告警 API 可用的 (start_time, end_time) ISO8601。

    参数:
        start_time: 起始时间描述或绝对时间
        end_time:   结束时间描述或绝对时间
        reference:  可选锚点「现在」，单元测试常用

    返回:
        (start_iso, end_iso) 或 None（无法解析时）

    注意:
        参数 reference 前的 * 表示其后必须关键字传参：reference=...
    """
    ref = _now(reference)
    s = (start_time or "").strip()
    e = (end_time or "").strip()

    # 两个都是绝对时间且成对 → 原样返回
    if s and e and _is_absolute_time(s) and _is_absolute_time(e):
        return s, e

    combined = s or e
    if s and e and not (_is_absolute_time(s) and _is_absolute_time(e)):
        combined = f"{s} {e}".strip()

    parsed = _parse_relative_phrase(combined, ref)
    if parsed:
        return _to_iso(parsed[0]), _to_iso(parsed[1])

    if s and not e:
        parsed = _parse_relative_phrase(s, ref)
        if parsed:
            return _to_iso(parsed[0]), _to_iso(parsed[1])

    # 整句中的日别 + 钟点区间（如 start=昨天 end=空 但原话含「昨天8点到9点」）
    if combined:
        clock_range = _parse_day_clock_range(combined, reference=ref)
        if clock_range:
            return _to_iso(clock_range[0]), _to_iso(clock_range[1])

    # 「2026-07-01 到 2026-07-03」类日期区间
    range_m = re.search(
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}).*?(?:到|至|~|-).*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        combined,
    )
    if range_m:
        a, b = range_m.group(1), range_m.group(2)
        a = re.sub(r"[年月]", "-", a).replace("日", "")
        b = re.sub(r"[年月]", "-", b).replace("日", "")
        try:
            start_dt = _start_of_day(datetime.fromisoformat(a))
            end_dt = _end_of_day(datetime.fromisoformat(b))
            return _to_iso(start_dt), _to_iso(end_dt)
        except ValueError:
            pass

    return None


def format_reference_hint(reference: datetime | None = None) -> str:
    """
    生成「当前时间」说明字符串，写入 System Prompt，让 LLM 知道「今天」是哪天。

    返回示例：2026-07-02 15:30:00 CST
    """
    ref = _now(reference)
    return ref.strftime("%Y-%m-%d %H:%M:%S %Z")


# ── 从用户原话抽取时间（Plan 预填 / preflight 兜底）──

# 相对时间短语：近三天、昨天、近30分钟等
_TIME_PHRASE_RE = re.compile(
    r"(?:近|最近|过去)"
    r"(?:[一二两三四五六七八九十\d]+|[半])?"
    r"(?:天|日|小时|分钟|秒|周|月|年|个?月)"
    r"|近三天|近一周|近一个月|近半年|近一年"
    r"|昨天|今天|本周|本月",
    re.I,
)

# 绝对日期时间（支持 YYYY-MM-DD HH:mm:ss、ISO8601 前缀等）
_DATETIME_TOKEN = (
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}(?:日)?"
    r"(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)?"
    r"(?:\s*[Zz]|\+?\d{2}:?\d{2})?"
)
_DATETIME_TOKEN_RE = re.compile(_DATETIME_TOKEN)

# 平台/API 字段名或 snake_case：startTime / start_time / 开始时间（冒号可省略）
_NAMED_START_RE = re.compile(
    rf"(?:start[\s_]?time|开始时间)\s*[:=]?\s*[\"']?({_DATETIME_TOKEN})[\"']?",
    re.I,
)
_NAMED_END_RE = re.compile(
    rf"(?:end[\s_]?time|结束时间)\s*[:=]?\s*[\"']?({_DATETIME_TOKEN})[\"']?",
    re.I,
)


def _normalize_datetime_token(raw: str) -> str:
    """将抽取到的日期时间片段规范为 resolve_alarm_time_range 可识别的形式。"""
    text = _normalize_time_text((raw or "").strip())
    text = re.sub(r"[年月]", "-", text).replace("日", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_day_clock_range(
    text: str,
    reference: datetime | None = None,
) -> tuple[datetime, datetime] | None:
    """
    解析「昨天8点到9点」「8点到8点10分」等日别 + 钟点区间。

    日别缺省视为今天；结束钟点未写「分」时取整点（如 8点到9点 → 08:00~09:00）。
    """
    msg = _normalize_time_text((text or "").strip())
    if not msg:
        return None

    m = re.search(
        r"(?:(昨天|昨日|今天|今日|前天)\s*)?"
        r"(\d{1,2})\s*点\s*(?:(\d{1,2})\s*分)?"
        r"\s*(?:到|至|~|—|-)\s*"
        r"(\d{1,2})\s*点\s*(?:(\d{1,2})\s*分)?",
        msg,
    )
    if not m:
        return None

    day_word = (m.group(1) or "").strip()
    h1 = int(m.group(2))
    min1 = int(m.group(3)) if m.group(3) else 0
    h2 = int(m.group(4))
    min2 = int(m.group(5)) if m.group(5) else 0

    if not (0 <= h1 <= 23 and 0 <= h2 <= 23 and 0 <= min1 <= 59 and 0 <= min2 <= 59):
        return None

    ref = _now(reference)
    today = _start_of_day(ref)
    if day_word in ("昨天", "昨日"):
        base = today - timedelta(days=1)
    elif day_word == "前天":
        base = today - timedelta(days=2)
    else:
        base = today

    start_dt = base.replace(hour=h1, minute=min1, second=0, microsecond=0)
    end_dt = base.replace(hour=h2, minute=min2, second=0, microsecond=0)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return start_dt, end_dt


def extract_time_phrase(message: str) -> str:
    """从用户消息中提取第一个相对时间短语（兼容 plan_confirm 旧接口）。"""
    m = _TIME_PHRASE_RE.search((message or "").strip())
    return m.group(0).strip() if m else ""


def extract_alarm_time_range_from_message(message: str) -> tuple[str, str]:
    """
    从用户原话提取告警查询/导出时间范围 (start_time, end_time)。

    优先级：
    1. 显式命名 startTime/endTime、start_time/end_time、开始/结束时间
    2. 句内按出现顺序的两个绝对时间
    3. 日别 + 钟点区间（昨天8点到9点、8点到8点10分）
    4. 相对时间短语（仅填 start_time，end_time 留空）
    5. 「YYYY-MM-DD 到 YYYY-MM-DD」类日期区间（写入 start_time 供 resolve 解析）
    """
    msg = _normalize_time_text((message or "").strip())
    if not msg:
        return "", ""

    start_match = _NAMED_START_RE.search(msg)
    end_match = _NAMED_END_RE.search(msg)
    if start_match or end_match:
        start_val = _normalize_datetime_token(start_match.group(1)) if start_match else ""
        end_val = _normalize_datetime_token(end_match.group(1)) if end_match else ""
        return start_val, end_val

    datetimes = [_normalize_datetime_token(m.group(0)) for m in _DATETIME_TOKEN_RE.finditer(msg)]
    datetimes = [d for d in datetimes if d]
    if len(datetimes) >= 2:
        return datetimes[0], datetimes[1]

    clock_range = _parse_day_clock_range(msg)
    if clock_range:
        return _to_iso(clock_range[0]), _to_iso(clock_range[1])

    phrase = extract_time_phrase(msg)
    if phrase:
        return phrase, ""

    range_m = re.search(
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}).*?(?:到|至|~|-).*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        msg,
    )
    if range_m:
        return f"{range_m.group(1)} 到 {range_m.group(2)}", ""

    if len(datetimes) == 1:
        return datetimes[0], ""

    # 整句语义解析（相对时间、自然语言区间等）
    resolved = resolve_alarm_time_range(msg, "")
    if resolved:
        return resolved[0], resolved[1]

    return "", ""


def enrich_alarm_time_args(
    args: dict[str, Any],
    *,
    user_message: str | None = None,
) -> dict[str, Any]:
    """
    历史兼容：不再从用户原话回填时间空槽。

    调用方（大模型 / HITL）须自行提供可解析的 start_time/end_time；
    本函数仅原样返回参数副本。``user_message`` 保留签名兼容。
    """
    _ = user_message
    return dict(args)
