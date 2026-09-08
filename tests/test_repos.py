# -*- coding: utf-8 -*-
"""저장소 발견과 git 수집 테스트."""
import datetime as dt
import subprocess

import pytest

from report.config import Config, Category
from report.repos import (
    Commit,
    _git,
    branch,
    commits,
    discover,
    git_root,
    to_rel,
    uncommitted,
)
from report.sessions import SessionEvent

DAY = dt.date(2026, 9, 8)


def run(cwd, *args):
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture
def repo(tmp_path):
    """커밋 3건이 있는 저장소. 2건은 본인, 1건은 타인. 날짜는 2026-09-08."""
    d = tmp_path / "dev" / "proj" / "app"
    d.mkdir(parents=True)
    run(d, "init", "-q", "-b", "main")
    run(d, "config", "user.name", "나")
    run(d, "config", "user.email", "me@example.com")

    env_times = [
        ("첫 커밋이다", "me@example.com", "나", "2026-09-08T09:29:00+09:00"),
        ("남의 커밋이다", "other@example.com", "남", "2026-09-08T10:00:00+09:00"),
        ("둘째 커밋이다", "me@example.com", "나", "2026-09-08T14:15:00+09:00"),
        ("어제 커밋이다", "me@example.com", "나", "2026-09-07T09:00:00+09:00"),
    ]
    for i, (subject, email, name, when) in enumerate(env_times):
        (d / "f{}.txt".format(i)).write_text(str(i), encoding="utf-8")
        run(d, "add", "-A")
        subprocess.run(
            ["git", "commit", "-q", "-m", subject,
             "--author", "{} <{}>".format(name, email),
             "--date", when],
            cwd=str(d), check=True,
            env={**_env(), "GIT_COMMITTER_DATE": when},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return d


def _env():
    import os
    return dict(os.environ)


def test_git_루트를_찾는다(repo):
    sub = repo / "src"
    sub.mkdir()
    assert git_root(sub) == str(repo.resolve())


def test_git_저장소가_아니면_None(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_root(plain) is None


def test_없는_경로면_None(tmp_path):
    assert git_root(tmp_path / "없음") is None


def test_dev_root_기준_상대경로로_바꾼다(tmp_path):
    dev = str(tmp_path / "dev")
    assert to_rel(str(tmp_path / "dev" / "proj" / "app"), dev) == "proj/app"


def test_dev_root_밖이면_절대경로를_돌려준다(tmp_path):
    assert to_rel(r"D:\other\thing", str(tmp_path / "dev")) == "D:/other/thing"


def test_브랜치를_읽는다(repo):
    assert branch(repo) == "main"


def test_본인_커밋만_돌려주고_타인은_센다(repo):
    got, skipped = commits(repo, DAY, ["me@example.com"])
    assert [c.subject for c in got] == ["첫 커밋이다", "둘째 커밋이다"]
    assert skipped == 1
    assert all(isinstance(c, Commit) for c in got)


def test_커밋_시각을_시분으로_준다(repo):
    got, _ = commits(repo, DAY, ["me@example.com"])
    assert [c.time for c in got] == ["09:29", "14:15"]


def test_다른_날_커밋은_빠진다(repo):
    got, _ = commits(repo, dt.date(2026, 9, 7), ["me@example.com"])
    assert [c.subject for c in got] == ["어제 커밋이다"]


def test_git_저장소가_아니면_커밋은_빈_목록(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert commits(plain, DAY, ["me@example.com"]) == ([], 0)


def test_미커밋_변경을_읽는다(repo):
    (repo / "새파일.txt").write_text("x", encoding="utf-8")
    (repo / "f0.txt").write_text("바뀜", encoding="utf-8")
    lines = uncommitted(repo)
    assert any("새파일.txt" in ln for ln in lines)
    assert any("f0.txt" in ln for ln in lines)


def test_깨끗하면_미커밋은_빈_목록(repo):
    assert uncommitted(repo) == []


def test_모르는_옵션이면_조용히_넘어가지_않고_RuntimeError(repo):
    """git 이 옵션을 못 알아들으면 None 으로 조용히 넘기지 말고 시끄럽게 터진다."""
    with pytest.raises(RuntimeError):
        _git(repo, "log", "--definitely-not-a-flag")


def test_저장소가_아닌_실패는_조용히_넘어가지_않고_RuntimeError(repo):
    """`저장소가 아니다`가 아닌 실패는 삼키면 안 된다.

    옛 동작은 exit code 가 0 이 아니면 전부 None 이었다. 그래서 깨진 인덱스나
    detected dubious ownership 같은 진짜 고장이 "커밋 0건 + (git 아님)"으로
    조용히 둔갑했다 — 근거를 다 모았다고 믿게 만드는 실패다.
    """
    with pytest.raises(RuntimeError, match="git 명령이 실패했다"):
        _git(repo, "cat-file", "-t", "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


def test_git_저장소가_아니면_조용히_None(tmp_path):
    """discover() 가 이 경로로 비git cwd 를 걸러낸다 — 여기는 조용해야 한다."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert _git(plain, "rev-parse", "--show-toplevel") is None


def test_커밋이_없는_저장소의_브랜치_조회도_조용히_None(tmp_path):
    """`git init` 만 한 새 폴더는 정상 상태다 — 여기서 터지면 수집이 통째로 죽는다."""
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    run(fresh, "init", "-q", "-b", "main")
    assert branch(fresh) is None


def make_config(dev_root, repos):
    cats = (Category(name="테스트구분", repos=tuple(repos)),)
    return Config(me=("me@example.com",), categories=cats, dev_root=dev_root)


def test_세션_cwd_와_config_저장소의_합집합을_돌려준다(repo, tmp_path):
    dev = str(tmp_path / "dev")
    events = [
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo / "src")),
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo)),
    ]
    got, _ = discover(events, make_config(dev, ["없는/저장소"]))
    # 세션에서 발견된 것 + config 에 등록된 것
    assert "proj/app" in got
    assert "없는/저장소" in got


def test_같은_저장소의_하위_디렉터리는_하나로_접힌다(repo, tmp_path):
    dev = str(tmp_path / "dev")
    (repo / "src").mkdir()
    events = [
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo / "src")),
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo)),
    ]
    got, _ = discover(events, make_config(dev, []))
    assert got.count("proj/app") == 1


def test_git_아닌_cwd_도_상대경로로_남긴다(repo, tmp_path):
    """교육 폴더처럼 git 이 아닌 작업 위치도 근거에서 빠지면 안 된다."""
    dev = tmp_path / "dev"
    plain = dev / "study" / "week04"
    plain.mkdir(parents=True)
    events = [SessionEvent(ts=dt.datetime.now(), cwd=str(plain))]
    got, _ = discover(events, make_config(str(dev), []))
    assert "study/week04" in got


def test_cwd_매핑도_같이_돌려준다(repo, tmp_path):
    """호출자가 이벤트를 저장소별로 접을 때 이 매핑을 그대로 쓴다 —
    같은 계산을 두 곳에서 하면 규칙이 갈리는 순간 이벤트가 엉뚱한
    저장소에 붙거나 아무 저장소에도 안 붙는다."""
    dev = str(tmp_path / "dev")
    (repo / "src").mkdir()
    events = [
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo / "src")),
        SessionEvent(ts=dt.datetime.now(), cwd=str(repo)),
    ]
    _, by_cwd = discover(events, make_config(dev, []))
    # 하위 디렉터리 cwd 도 git 루트의 상대경로로 접힌다
    assert by_cwd[str(repo / "src")] == "proj/app"
    assert by_cwd[str(repo)] == "proj/app"
    # 모든 이벤트 cwd 에 항목이 있어야 한다 (호출자가 KeyError 없이 쓴다)
    assert set(by_cwd) == {str(repo / "src"), str(repo)}
