import json

from scripts.daily_pipeline import main as pipeline_main


def test_daily_pipeline_cli_dry_run(tmp_path, capsys):
    pipeline_cfg = tmp_path / "pipeline.yaml"
    pipeline_cfg.write_text(
        json.dumps(
            {
                "pipeline": {
                    "default_top_n": 3,
                    "recommendation_dir": str(tmp_path / "recs"),
                    "report_dir": str(tmp_path / "reports"),
                    "db_path": str(tmp_path / "recs.db"),
                    "run_meta_path": str(tmp_path / "pipeline_runs.jsonl"),
                },
                "error_handling": {"retry_attempts": 1, "retry_backoff_seconds": [0]},
                "logging": {"level": "INFO", "format": "%(message)s"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    data_source_cfg = tmp_path / "data_source.yaml"
    data_source_cfg.write_text(
        json.dumps(
            {
                "default_source": "tushare",
                "sources": {"tushare": {"cache_dir": str(tmp_path / "cache")}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pipeline_main(
        [
            "--date",
            "20260113",
            "--config",
            str(pipeline_cfg),
            "--data-source-config",
            str(data_source_cfg),
            "--dry-run",
        ]
    )

    out = capsys.readouterr().out
    result = json.loads(out)
    assert result["run_date"] == "2026-01-13"
    assert result["status"] in {"success", "partial"}

    rec_dir = tmp_path / "recs"
    assert (rec_dir / "20260113.json").exists()
    assert (rec_dir / "20260113_5d.csv").exists()
    assert (rec_dir / "20260113.md").exists()
    assert (tmp_path / "pipeline_runs.jsonl").exists()


def test_daily_pipeline_cli_dry_run_with_odp_source(tmp_path, capsys):
    pipeline_cfg = tmp_path / "pipeline.yaml"
    pipeline_cfg.write_text(
        json.dumps(
            {
                "pipeline": {
                    "default_top_n": 3,
                    "recommendation_dir": str(tmp_path / "recs"),
                    "report_dir": str(tmp_path / "reports"),
                    "db_path": str(tmp_path / "recs.db"),
                    "run_meta_path": str(tmp_path / "pipeline_runs.jsonl"),
                },
                "error_handling": {"retry_attempts": 1, "retry_backoff_seconds": [0]},
                "logging": {"level": "INFO", "format": "%(message)s"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    data_source_cfg = tmp_path / "data_source.yaml"
    data_source_cfg.write_text(
        json.dumps(
            {
                "default_source": "odp",
                "sources": {"odp": {"cache_dir": str(tmp_path / "cache"), "provider": "yfinance"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pipeline_main(
        [
            "--date",
            "20260113",
            "--config",
            str(pipeline_cfg),
            "--data-source-config",
            str(data_source_cfg),
            "--dry-run",
        ]
    )

    out = capsys.readouterr().out
    result = json.loads(out)
    assert result["run_date"] == "2026-01-13"
    assert result["status"] in {"success", "partial"}
