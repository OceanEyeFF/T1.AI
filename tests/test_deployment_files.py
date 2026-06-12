"""
Smoke tests for deployment files (Task 3.3).
"""
import os
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
        ["bash", "-n", "scripts/daily_pipeline.sh"],
        capture_output=True,
        text=True
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


def test_production_scheduler_doc_exists():
    """Test that production scheduler documentation exists."""
    doc_path = Path("docs/modules/production_scheduler.md")
    assert doc_path.exists(), "docs/modules/production_scheduler.md does not exist"

    # Check that documentation covers both deployment options
    content = doc_path.read_text()
    assert "Cron" in content, "Documentation missing Cron section"
    assert "Systemd" in content, "Documentation missing Systemd section"
    assert "错误排查" in content or "troubleshooting" in content.lower(), \
        "Documentation missing troubleshooting section"
    assert "TUSHARE_TOKEN" in content, "Documentation missing token setup"


def test_deployment_directory_structure():
    """Test that deployment directory has all required files."""
    deployment_dir = Path("deployment")
    assert deployment_dir.exists(), "deployment directory does not exist"

    required_files = [
        "crontab.example",
        "daily-pipeline.service",
        "daily-pipeline.timer"
    ]

    for filename in required_files:
        filepath = deployment_dir / filename
        assert filepath.exists(), f"Missing deployment file: {filename}"
