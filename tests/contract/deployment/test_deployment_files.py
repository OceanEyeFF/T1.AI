"""
Smoke tests for deployment files (Task 3.3).
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path


def test_daily_pipeline_sh_exists():
    """Test that daily_pipeline.sh exists and is executable."""
    script_path = Path("scripts/daily_pipeline.sh")
    assert script_path.exists(), "daily_pipeline.sh does not exist"

    # Check executable permission
    st = os.stat(script_path)
    is_executable = bool(st.st_mode & stat.S_IXUSR)
    assert is_executable, "daily_pipeline.sh is not executable"


def test_daily_pipeline_sh_syntax():
    """Test that daily_pipeline.sh has valid bash syntax."""
    result = subprocess.run(
        ["bash", "-n", "scripts/daily_pipeline.sh"], capture_output=True, text=True
    )
    assert result.returncode == 0, f"Shell script has syntax errors: {result.stderr}"


def test_crontab_example_exists():
    """Test that crontab.example exists."""
    crontab_path = Path("deployment/crontab.example")
    assert crontab_path.exists(), "deployment/crontab.example does not exist"

    # Check that it contains the expected cron schedule
    content = crontab_path.read_text()
    assert "15 15 * * 1-5" in content, "Crontab missing expected schedule"
    assert "TUSHARE_TOKEN" in content, "Crontab missing TUSHARE_TOKEN"


def test_systemd_service_exists():
    """Test that systemd service file exists."""
    service_path = Path("deployment/daily-pipeline.service")
    assert service_path.exists(), "deployment/daily-pipeline.service does not exist"

    # Check that it contains required sections
    content = service_path.read_text()
    assert "[Unit]" in content, "Service file missing [Unit] section"
    assert "[Service]" in content, "Service file missing [Service] section"
    assert "[Install]" in content, "Service file missing [Install] section"
    assert "ExecStart=" in content, "Service file missing ExecStart"


def test_systemd_timer_exists():
    """Test that systemd timer file exists."""
    timer_path = Path("deployment/daily-pipeline.timer")
    assert timer_path.exists(), "deployment/daily-pipeline.timer does not exist"

    # Check that it contains required sections
    content = timer_path.read_text()
    assert "[Unit]" in content, "Timer file missing [Unit] section"
    assert "[Timer]" in content, "Timer file missing [Timer] section"
    assert "[Install]" in content, "Timer file missing [Install] section"
    assert "OnCalendar=" in content, "Timer file missing OnCalendar"


def test_daily_pipeline_ops_doc_exists():
    """Deployment ops doc exists after MS-R3 archive cleanup."""
    doc_path = Path("docs/guides/daily_pipeline_ops.md")
    assert doc_path.exists(), "docs/guides/daily_pipeline_ops.md does not exist"
    content = doc_path.read_text(encoding="utf-8")
    assert "daily_pipeline" in content
    assert "deployment" in content.lower() or "systemd" in content.lower() or "cron" in content.lower()


def test_daily_pipeline_sh_content_contract():
    """wrapper 内容合同：新 config 路径 / 三区日志目录 / .env 加载 / 退出码透传。"""
    text = Path("scripts/daily_pipeline.sh").read_text(encoding="utf-8")
    assert "--config inputs/configs/pipeline.toml" in text
    assert "mkdir -p workspace/runs" in text
    assert 'source "$PROJECT_ROOT/.env"' in text
    assert "EXIT_CODE=${PIPESTATUS[0]}" in text
    assert "exit $EXIT_CODE" in text
    # 旧路径不得回归
    assert "configs/pipeline.yaml" not in text
    assert "mkdir -p logs" not in text
    # set -u 下引用 PYTHONPATH 必须带缺省（曾导致无 PYTHONPATH 环境开箱即崩）
    assert '"$PROJECT_ROOT:${PYTHONPATH:-}"' in text


def test_daily_pipeline_sh_runtime_contract(tmp_path):
    """wrapper 运行合同：无 PYTHONPATH 环境可运行、.env 加载、参数透传、退出码透传。"""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2("scripts/daily_pipeline.sh", root / "scripts/daily_pipeline.sh")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$@" > "$CAPTURE_ARGS"\n'
        '[ "$FROM_DOTENV" = yes ] || { echo "dotenv not loaded" >&2; exit 9; }\n'
        'exit 7\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    (root / ".env").write_text("FROM_DOTENV=yes\n", encoding="utf-8")

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)  # 回归锁：曾因 set -u + 未定义 PYTHONPATH 直接崩
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["CAPTURE_ARGS"] = str(tmp_path / "args.txt")

    proc = subprocess.run(
        ["bash", str(root / "scripts/daily_pipeline.sh"), "20260113"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 7, proc.stderr + proc.stdout  # 退出码透传
    args_text = (tmp_path / "args.txt").read_text(encoding="utf-8")
    assert "--config" in args_text and "inputs/configs/pipeline.toml" in args_text
    assert "--date" in args_text and "20260113" in args_text

    log = (root / "workspace/runs/pipeline.log").read_text(encoding="utf-8")
    assert "Daily Pipeline Start" in log
    assert "Daily Pipeline End" in log
    assert "Exit Code: 7" in log
