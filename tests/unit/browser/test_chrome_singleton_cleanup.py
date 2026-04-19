from pathlib import Path

from drission_kernel.session import _parse_singleton_owner, cleanup_stale_chromium_singleton


def _write_singleton_files(profile_dir: Path, lock_owner: str) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "SingletonCookie").write_text("cookie", encoding="utf-8")
    (profile_dir / "SingletonSocket").write_text("socket", encoding="utf-8")
    (profile_dir / "SingletonLock").symlink_to(lock_owner)


def test_parse_singleton_owner_from_symlink(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    lock_path = profile_dir / "SingletonLock"
    lock_path.symlink_to("host-a-1234")

    host, pid = _parse_singleton_owner(lock_path)

    assert host == "host-a"
    assert pid == 1234


def test_cleanup_removes_stale_lock_on_host_mismatch(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    _write_singleton_files(profile_dir, "other-host-8")

    cleaned = cleanup_stale_chromium_singleton(
        profile_dir,
        current_host="this-host",
        pid_alive_checker=lambda _: True,
    )

    assert cleaned is True
    assert not (profile_dir / "SingletonLock").exists()
    assert not (profile_dir / "SingletonLock").is_symlink()
    assert not (profile_dir / "SingletonCookie").exists()
    assert not (profile_dir / "SingletonSocket").exists()


def test_cleanup_keeps_active_lock_on_same_host(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    _write_singleton_files(profile_dir, "same-host-88")

    cleaned = cleanup_stale_chromium_singleton(
        profile_dir,
        current_host="same-host",
        pid_alive_checker=lambda _: True,
    )

    assert cleaned is False
    assert (profile_dir / "SingletonLock").is_symlink()
    assert (profile_dir / "SingletonCookie").exists()
    assert (profile_dir / "SingletonSocket").exists()


def test_cleanup_removes_dead_lock_on_same_host(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    _write_singleton_files(profile_dir, "same-host-99")

    cleaned = cleanup_stale_chromium_singleton(
        profile_dir,
        current_host="same-host",
        pid_alive_checker=lambda _: False,
    )

    assert cleaned is True
    assert not (profile_dir / "SingletonLock").exists()
    assert not (profile_dir / "SingletonLock").is_symlink()
    assert not (profile_dir / "SingletonCookie").exists()
    assert not (profile_dir / "SingletonSocket").exists()
