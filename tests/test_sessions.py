# -*- coding: utf-8 -*-
"""세션 jsonl 파싱 테스트 — 이벤트별 cwd 로 집계해야 한다."""
import datetime as dt
import json

from report.sessions import load_events

DAY = dt.date(2026, 9, 8)

# 아래 픽스처의 timestamp 는 UTC(Z)이고, 기대값은 KST(UTC+9) 처럼 UTC 보다
# 앞선 로컬 시간대를 가정한다. load_events 는 이벤트를 로컬 시간대로 옮겨
# 날짜를 비교하므로, 예를 들어 "2026-09-08T00:10:00Z" 가 그날 이벤트로 잡히는
# 것은 오프셋이 0 이상일 때만이다. 대략 UTC+0 서쪽(음수 오프셋)에서 돌리면
# 날짜가 하루 밀려 실패한다(반대쪽 한계는 대략 UTC+15). 다른 시간대에서
# 실패하면 픽스처의 시각을 정오 근처로 옮긴다.


def line(ts, cwd, **extra):
    o = {"timestamp": ts, "cwd": cwd}
    o.update(extra)
    return json.dumps(o, ensure_ascii=False)


def user_line(ts, cwd, text):
    return line(
        ts,
        cwd,
        type="user",
        userType="external",
        message={"content": [{"type": "text", "text": text}]},
    )


def write_session(root, name, lines):
    d = root / "proj"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_이벤트마다_cwd_를_따로_본다(tmp_path):
    """한 세션이 디렉터리를 옮기면 양쪽이 다 잡혀야 한다."""
    write_session(
        tmp_path,
        "a.jsonl",
        [
            line("2026-09-08T00:10:00.000Z", r"C:\dev\front"),
            line("2026-09-08T01:10:00.000Z", r"C:\dev\infra"),
            line("2026-09-08T02:10:00.000Z", r"C:\dev\infra"),
        ],
    )
    events = load_events(DAY, tmp_path)
    cwds = [e.cwd for e in events]
    assert cwds.count(r"C:\dev\front") == 1
    assert cwds.count(r"C:\dev\infra") == 2


def test_다른_날짜는_버린다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            line("2026-09-07T05:00:00.000Z", r"C:\dev\front"),
            line("2026-09-08T05:00:00.000Z", r"C:\dev\front"),
            line("2026-09-09T05:00:00.000Z", r"C:\dev\front"),
        ],
    )
    assert len(load_events(DAY, tmp_path)) == 1


def test_사용자_프롬프트만_담는다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            user_line("2026-09-08T05:00:00.000Z", r"C:\dev\front", "핸드오프 확인해줘"),
            line(
                "2026-09-08T05:01:00.000Z",
                r"C:\dev\front",
                type="assistant",
                message={"content": [{"type": "text", "text": "네"}]},
            ),
        ],
    )
    events = load_events(DAY, tmp_path)
    prompts = [e.prompt for e in events if e.prompt]
    assert prompts == ["핸드오프 확인해줘"]


def test_시스템_리마인더_프롬프트는_버린다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            user_line("2026-09-08T05:00:00.000Z", r"C:\dev\front", "<system-reminder>x"),
            user_line("2026-09-08T05:01:00.000Z", r"C:\dev\front", "진짜 요청"),
        ],
    )
    prompts = [e.prompt for e in load_events(DAY, tmp_path) if e.prompt]
    assert prompts == ["진짜 요청"]


def test_ignore_prompts_에_걸리면_버린다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            user_line(
                "2026-09-08T05:00:00.000Z",
                r"C:\dev\front",
                "Review this change for security vulnerabilities. Changed files: ...",
            ),
            user_line("2026-09-08T05:01:00.000Z", r"C:\dev\front", "사람이 시킨 일"),
        ],
    )
    events = load_events(
        DAY, tmp_path, ignore_prompts=["Review this change for security vulnerabilities"]
    )
    prompts = [e.prompt for e in events if e.prompt]
    assert prompts == ["사람이 시킨 일"]
    # 프롬프트만 버리고 이벤트 자체는 남는다 (활동량 집계에 쓰인다)
    assert len(events) == 2


def test_깨진_줄과_timestamp_없는_줄은_건너뛴다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            "{{{ 깨진 json",
            json.dumps({"cwd": r"C:\dev\front"}),
            line("2026-09-08T05:00:00.000Z", r"C:\dev\front"),
        ],
    )
    assert len(load_events(DAY, tmp_path)) == 1


def test_cwd_없는_줄은_건너뛴다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            json.dumps({"timestamp": "2026-09-08T05:00:00.000Z"}),
            line("2026-09-08T05:00:00.000Z", r"C:\dev\front"),
        ],
    )
    assert len(load_events(DAY, tmp_path)) == 1


def test_시간_오름차순으로_정렬한다(tmp_path):
    write_session(
        tmp_path,
        "a.jsonl",
        [
            line("2026-09-08T09:00:00.000Z", r"C:\dev\b"),
            line("2026-09-08T01:00:00.000Z", r"C:\dev\a"),
        ],
    )
    events = load_events(DAY, tmp_path)
    assert [e.cwd for e in events] == [r"C:\dev\a", r"C:\dev\b"]


def test_하위_디렉터리를_재귀로_찾는다(tmp_path):
    deep = tmp_path / "x" / "y" / "z"
    deep.mkdir(parents=True)
    (deep / "s.jsonl").write_text(
        line("2026-09-08T05:00:00.000Z", r"C:\dev\front") + "\n", encoding="utf-8"
    )
    assert len(load_events(DAY, tmp_path)) == 1
