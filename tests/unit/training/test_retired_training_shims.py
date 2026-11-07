from __future__ import annotations

import importlib
import warnings

import pytest


def test_retired_training_namespace_is_explicit_and_fail_closed() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        module = importlib.import_module("ashare_lab.training")
        module = importlib.reload(module)

    assert any("retired" in str(item.message) for item in caught)
    with pytest.raises(RuntimeError, match="retired"):
        module.IncrementalTrainer()


def test_retired_training_module_paths_remain_importable() -> None:
    finetune = importlib.import_module("ashare_lab.training.mtl_finetune")
    trainer = importlib.import_module("ashare_lab.training.trainer")

    with pytest.raises(RuntimeError, match="retired"):
        finetune.TrainingGate()
    with pytest.raises(RuntimeError, match="retired"):
        trainer.Trainer()


def test_retired_train_mtl_cli_fails_with_a_migration_message(capsys) -> None:
    from scripts.train_mtl import main

    with pytest.raises(SystemExit) as exc:
        main([])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert "retired" in captured.err
