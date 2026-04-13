#!/usr/bin/env python3
"""
生成各类 ICS 日历文件：
  ics/school.ics    — 学校校历
  ics/life.ics      — 垃圾分类 + 账单提醒
  ics/work.ics      — 兼职排班
  ics/holidays.ics  — 日本公共节假日（从 Google 拉取）
  ics/merged.ics    — 全部合并
"""
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ICS_DIR = ROOT / "ics"
ICS_DIR.mkdir(exist_ok=True)

GOOGLE_ICS_URL = (
    "https://www.google.com/calendar/ical/"
    "ja.japanese%23holiday%40group.v.calendar.google.com/public/basic.ics"
)

WEEKDAY_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2,
    "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6,
}


# ---------------------------------------------------------------------------
# ICS helpers
# ---------------------------------------------------------------------------

def ics_escape(text: str) -> str:
    return (text.replace("\\", "\\\\")
                .replace(";", r"\;")
                .replace(",", r"\,")
                .replace("\n", r"\n"))


def dtstamp_fixed(d: date) -> str:
    """使用日期精度的时间戳，避免每次运行都产生 diff。"""
    return f"{d.strftime('%Y%m%d')}T000000Z"


def make_vevent(uid: str, summary: str, start: date,
                end: date | None = None, description: str = "",
                start_time: str = "", end_time: str = "",
                alarm_days_before: int = 0) -> str:
    """生成一个 VEVENT 块。"""
    stamp = dtstamp_fixed(start)
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}"]

    if start_time and end_time:
        # 带具体时间的事件（兼职排班）
        dt_start = f"{start.strftime('%Y%m%d')}T{start_time.replace(':', '')}00"
        dt_end = f"{start.strftime('%Y%m%d')}T{end_time.replace(':', '')}00"
        lines += [f"DTSTART;TZID=Asia/Tokyo:{dt_start}",
                  f"DTEND;TZID=Asia/Tokyo:{dt_end}"]
    else:
        # 全天事件
        end_date = end or (start + timedelta(days=1))
        lines += [f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                  f"DTEND;VALUE=DATE:{end_date.strftime('%Y%m%d')}"]

    lines += [f"SUMMARY:{ics_escape(summary)}", "TRANSP:TRANSPARENT"]
    if description:
        lines.append(f"DESCRIPTION:{ics_escape(description)}")

    if alarm_days_before > 0:
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{ics_escape(summary)}",
            f"TRIGGER:-P{alarm_days_before}D",
            "END:VALARM",
        ]

    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def write_ics(path: Path, cal_name: str, prodid: str, events: list[str]) -> None:
    header = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{prodid}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        f"X-WR-CALDESC:{cal_name}",
        "X-WR-TIMEZONE:Asia/Tokyo",
    ])
    body = "\r\n".join(events)
    path.write_text(header + "\r\n" + body + "\r\nEND:VCALENDAR\r\n", encoding="utf-8")


PRODID = "-//Joewon9//Academic-Calendar//CN"


# ---------------------------------------------------------------------------
# School calendar
# ---------------------------------------------------------------------------

def build_school_events() -> list[str]:
    data = yaml.safe_load((DATA_DIR / "school.yaml").read_text(encoding="utf-8"))
    events = []
    for date_str, summary in sorted(data["events"].items()):
        d = date.fromisoformat(date_str)
        uid = f"school-{date_str}-{summary}@joewon9.calendar"
        events.append(make_vevent(uid, summary, d))
    return events


# ---------------------------------------------------------------------------
# Garbage collection calendar
# ---------------------------------------------------------------------------

def expand_recurring(rule: dict, start: date, end: date) -> list[date]:
    """将周期规则展开为具体日期列表。"""
    target_weekdays = [WEEKDAY_MAP[d] for d in rule["days"]]
    frequency = rule["frequency"]
    result = []

    if frequency == "weekly":
        cur = start
        while cur <= end:
            if cur.weekday() in target_weekdays:
                result.append(cur)
            cur += timedelta(days=1)

    elif frequency == "biweekly":
        ref = date.fromisoformat(rule["reference_date"]) if "reference_date" in rule else start
        # 找到 ref 所在周的目标星期
        for wd in target_weekdays:
            # 计算 ref 所在周该星期几的日期
            ref_week_day = ref - timedelta(days=ref.weekday()) + timedelta(days=wd)
            cur = ref_week_day
            # 向前对齐到 start
            while cur < start:
                cur += timedelta(weeks=2)
            while cur <= end:
                result.append(cur)
                cur += timedelta(weeks=2)

    return sorted(set(result))


def build_garbage_events() -> list[str]:
    data = yaml.safe_load((DATA_DIR / "garbage.yaml").read_text(encoding="utf-8"))
    # 使用学校校历的覆盖范围作为生成范围
    school_data = yaml.safe_load((DATA_DIR / "school.yaml").read_text(encoding="utf-8"))
    start = date.fromisoformat(school_data["meta"]["coverage"]["start"])
    end = date.fromisoformat(school_data["meta"]["coverage"]["end"])

    events = []
    for rule in data["rules"]:
        name = rule["name"]
        note = rule.get("note", "")
        for d in expand_recurring(rule, start, end):
            uid = f"garbage-{name}-{d.isoformat()}@joewon9.calendar"
            events.append(make_vevent(uid, name, d, description=note))
    return events


# ---------------------------------------------------------------------------
# Bills calendar
# ---------------------------------------------------------------------------

def build_bill_events() -> list[str]:
    data = yaml.safe_load((DATA_DIR / "bills.yaml").read_text(encoding="utf-8"))
    school_data = yaml.safe_load((DATA_DIR / "school.yaml").read_text(encoding="utf-8"))
    start = date.fromisoformat(school_data["meta"]["coverage"]["start"])
    end = date.fromisoformat(school_data["meta"]["coverage"]["end"])

    events = []
    for bill in data["bills"]:
        name = bill["name"]
        day = bill["day_of_month"]
        alarm = bill.get("reminder_days_before", 3)

        # 遍历覆盖范围内每个月
        cur_year, cur_month = start.year, start.month
        while True:
            try:
                d = date(cur_year, cur_month, day)
            except ValueError:
                # 该月没有这一天（如2月30日），跳过
                pass
            else:
                if start <= d <= end:
                    uid = f"bill-{name}-{d.isoformat()}@joewon9.calendar"
                    events.append(make_vevent(uid, f"{name}到期", d,
                                             alarm_days_before=alarm))
            if cur_month == 12:
                cur_year += 1
                cur_month = 1
            else:
                cur_month += 1
            if date(cur_year, cur_month, 1) > end:
                break
    return events


# ---------------------------------------------------------------------------
# Part-time work calendar
# ---------------------------------------------------------------------------

def build_parttime_events() -> list[str]:
    data = yaml.safe_load((DATA_DIR / "parttime.yaml").read_text(encoding="utf-8"))
    shifts = data.get("shifts") or []
    events = []
    for shift in shifts:
        d = date.fromisoformat(shift["date"])
        start_t = shift["start"]
        end_t = shift["end"]
        location = shift.get("location", "")
        note = shift.get("note", "")
        summary = "兼职" + (f" · {location}" if location else "")
        description = note
        uid = f"work-{shift['date']}-{start_t}@joewon9.calendar"
        events.append(make_vevent(uid, summary, d,
                                  start_time=start_t, end_time=end_t,
                                  description=description))
    return events


# ---------------------------------------------------------------------------
# Japan public holidays (from Google)
# ---------------------------------------------------------------------------

def fetch_holidays_ics() -> str:
    req = urllib.request.Request(
        GOOGLE_ICS_URL,
        headers={"User-Agent": "Mozilla/5.0",
                 "Accept": "text/calendar,*/*;q=0.8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[警告] 无法获取日本节假日数据：{e}")
        return ""


def extract_holiday_events(ics_text: str) -> list[str]:
    if not ics_text:
        return []
    blocks, current, in_event = [], [], False
    for line in ics_text.splitlines():
        line = line.rstrip("\r\n")
        if line == "BEGIN:VEVENT":
            in_event, current = True, [line]
        elif line == "END:VEVENT" and in_event:
            current.append(line)
            blocks.append("\r\n".join(current))
            in_event, current = False, []
        elif in_event:
            current.append(line)
    return blocks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("正在生成日历文件...")

    school_events = build_school_events()
    garbage_events = build_garbage_events()
    bill_events = build_bill_events()
    parttime_events = build_parttime_events()

    print("正在获取日本节假日...")
    holidays_raw = fetch_holidays_ics()
    holiday_events = extract_holiday_events(holidays_raw)

    # school.ics
    write_ics(ICS_DIR / "school.ics", "2026学年校历", PRODID, school_events)
    print(f"  school.ics   — {len(school_events)} 个事件")

    # life.ics（垃圾 + 账单）
    life_events = garbage_events + bill_events
    write_ics(ICS_DIR / "life.ics", "生活日历", PRODID, life_events)
    print(f"  life.ics     — {len(life_events)} 个事件 "
          f"（垃圾:{len(garbage_events)} 账单:{len(bill_events)}）")

    # work.ics
    write_ics(ICS_DIR / "work.ics", "兼职排班", PRODID, parttime_events)
    print(f"  work.ics     — {len(parttime_events)} 个事件")

    # holidays.ics
    if holiday_events:
        write_ics(ICS_DIR / "holidays.ics", "日本节假日", PRODID, holiday_events)
        print(f"  holidays.ics        — {len(holiday_events)} 个事件")

    # school_holidays.ics（校历 + 日本节假日）
    school_holiday_events = school_events + holiday_events
    write_ics(ICS_DIR / "school_holidays.ics", "校历 & 日本节假日", PRODID, school_holiday_events)
    print(f"  school_holidays.ics — {len(school_holiday_events)} 个事件（校历 + 节假日）")

    # merged.ics
    all_events = school_events + life_events + parttime_events + holiday_events
    write_ics(ICS_DIR / "merged.ics", "日本生活日历", PRODID, all_events)
    print(f"  merged.ics          — {len(all_events)} 个事件（全部合并）")

    print("完成。")


if __name__ == "__main__":
    main()
