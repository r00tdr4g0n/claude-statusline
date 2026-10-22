#!/usr/bin/env python3
"""Claude Code 상태표시줄.

구간: 폴더 | 모델 | effort | 컨텍스트 | 5시간 한도 | 7일 한도
구간 사이는 세로줄로 나누고, 사용률은 가로 게이지 바로 보여준다.
바의 찬 부분이 쓴 만큼, 빈 부분이 남은 만큼이다.
"""

import json
import shutil
import sys
import unicodedata

#	구간 구분자. 앞뒤 공백까지 포함한 폭이 그대로 화면 폭에 들어간다.
SEPARATOR = " | "

#	구간 앞에 붙는 아이콘. 전부 두 칸을 먹는 문자라 폭 계산에서 2로 센다.
#	이모지가 싫으면 아래 한 줄짜리 기호로 바꿔도 된다(폭 1로 자동 계산됨).
#	    ICON_DIR, ICON_MODEL, ICON_EFFORT = "⌂", "◈", "⚑"
#	    ICON_CONTEXT, ICON_FIVE_HOUR, ICON_SEVEN_DAY = "▤", "◔", "▣"
ICON_DIR = "📁"
ICON_MODEL = "🤖"
ICON_EFFORT = "🧠"
ICON_CONTEXT = "📊"
ICON_FIVE_HOUR = "⏳"
ICON_SEVEN_DAY = "📅"

RESET = "\033[0m"

#	256색 인덱스. 배경 없이 글자색만 쓴다.
COLOR_SEPARATOR = 240  # 어두운 회색
COLOR_DIR = 81  # 하늘
COLOR_MODEL = 141  # 연보라
COLOR_EFFORT = 218  # 연분홍
COLOR_CONTEXT = 80  # 청록
COLOR_FIVE_HOUR = 114  # 연두
COLOR_SEVEN_DAY = 176  # 자주

#	게이지 바에서 아직 안 쓴 칸의 색. 남은 양이 보이되 튀지는 않게.
COLOR_BAR_EMPTY = 238

#	평소에는 구간마다 제 색을 쓰고, 수치가 올라갔을 때만 이 색이 덮는다.
ALERT_STEPS = (
    (90, 196),  # 빨강
    (75, 208),  # 주황
)

#	게이지 바 칸수. 늘리면 눈금이 촘촘해지고 줄 길이도 같이 는다.
BAR_WIDTH = 8

BAR_FULL = "█"  # █
BAR_EMPTY = "░"  # ░

#	한 칸을 8등분한 조각. 15% 처럼 작은 값도 바에 흔적이 남게 한다.
BAR_EIGHTHS = " ▏▎▍▌▋▊▉"

#	터미널 폭을 못 읽었을 때 쓸 값. 좁게 잡으면 멀쩡한 구간을 잘라 먹는다.
FALLBACK_COLUMNS = 120


def display_width(text):
    """화면에서 차지하는 칸수. 이모지와 한글은 두 칸을 먹는다."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def fg(index):
    return "\033[38;5;{}m".format(index)


def paint(index, text):
    return fg(index) + text + RESET


def alert_color(percent, base):
    for limit, color in ALERT_STEPS:
        if percent >= limit:
            return color
    return base


def to_percent(value):
    """None 이거나 숫자가 아니면 None 을 준다. 구간 자체를 빼기 위한 신호다."""
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def bar(percent, width=BAR_WIDTH):
    """(찬 부분, 빈 부분). 두 부분을 다른 색으로 칠하려고 나눠서 준다."""
    percent = max(0, min(100, percent))
    filled = percent / 100.0 * width

    full = int(filled)
    used = BAR_FULL * full
    rest = width - full

    if rest > 0:
        eighth = int((filled - full) * 8)

        #	0 이 아닌데 한 조각도 안 차면 0% 와 구별이 안 된다.
        #	쓰기 시작한 것은 가장 얇은 조각으로라도 보여준다.
        if eighth == 0 and percent > 0 and full == 0:
            eighth = 1

        if eighth > 0:
            used += BAR_EIGHTHS[eighth]
            rest -= 1

    return used, BAR_EMPTY * rest


def directory_name(payload):
    raw = (payload.get("workspace") or {}).get("current_dir") or payload.get("cwd") or ""
    parts = [p for p in raw.replace("\\", "/").rstrip("/").split("/") if p]
    return parts[-1] if parts else "?"


def model_label(payload):
    name = (payload.get("model") or {}).get("display_name") or "?"

    #	"Opus 5 (1M context)" 처럼 괄호가 길다. 괄호는 떼고 1M 만 남긴다.
    head = name.split(" (")[0].strip()
    if "1M" in name and "1M" not in head:
        head = head + " 1M"

    if payload.get("fast_mode"):
        head = head + " fast"
    return head


def gauge_segment(icon, label, percent, base_color):
    """'📊 ctx ██▍░░░░░ 15%' 한 구간. (민글자, 색입힌글자) 로 준다."""
    color = alert_color(percent, base_color)
    used, empty = bar(percent)

    plain = "{} {} {}{} {}%".format(icon, label, used, empty, percent)
    painted = "{} {} {}{} {}".format(
        icon,
        paint(color, label),
        paint(color, used) if used else "",
        paint(COLOR_BAR_EMPTY, empty) if empty else "",
        paint(color, "{}%".format(percent)),
    )
    return plain, painted


def build_segments(payload):
    """(민글자, 색입힌글자) 목록. 값이 없는 구간은 아예 만들지 않는다."""
    def labelled(icon, color, text):
        return ("{} {}".format(icon, text), "{} {}".format(icon, paint(color, text)))

    segments = [
        labelled(ICON_DIR, COLOR_DIR, directory_name(payload)),
        labelled(ICON_MODEL, COLOR_MODEL, model_label(payload)),
    ]

    level = (payload.get("effort") or {}).get("level")
    if level:
        segments.append(labelled(ICON_EFFORT, COLOR_EFFORT, level))

    context = to_percent((payload.get("context_window") or {}).get("used_percentage"))
    if context is not None:
        segments.append(
            gauge_segment(ICON_CONTEXT, "ctx", context, COLOR_CONTEXT)
        )

    limits = payload.get("rate_limits") or {}
    for key, icon, label, base in (
        ("five_hour", ICON_FIVE_HOUR, "5h", COLOR_FIVE_HOUR),
        ("seven_day", ICON_SEVEN_DAY, "7d", COLOR_SEVEN_DAY),
    ):
        percent = to_percent((limits.get(key) or {}).get("used_percentage"))
        if percent is not None:
            segments.append(gauge_segment(icon, label, percent, base))

    return segments


def visible_width(segments):
    text = sum(display_width(plain) for plain, _ in segments)
    return text + display_width(SEPARATOR) * max(0, len(segments) - 1)


def fit(segments):
    """폭이 모자라면 뒤쪽 구간부터 접는다. 폴더 구간 하나는 끝까지 남긴다."""
    try:
        columns = shutil.get_terminal_size((FALLBACK_COLUMNS, 24)).columns
    except Exception:
        columns = FALLBACK_COLUMNS
    if columns <= 0:
        columns = FALLBACK_COLUMNS

    while len(segments) > 1 and visible_width(segments) > columns:
        segments.pop()
    return segments


def render(segments):
    divider = paint(COLOR_SEPARATOR, SEPARATOR)
    return divider.join(painted for _, painted in segments)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    #	Windows 기본 인코딩(cp949)으로는 블록 문자를 못 쓴다.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    sys.stdout.write(render(fit(build_segments(payload))))


if __name__ == "__main__":
    main()
