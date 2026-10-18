from unittest.mock import MagicMock

from bson import ObjectId

from manage_records import main, parser, run_action


def test_write_command_requires_opt_in(capsys):
    assert main(["create", "unused.json"]) == 1
    assert "--allow-writes" in capsys.readouterr().out


def test_csv_mode_cannot_manage_database(monkeypatch, capsys):
    monkeypatch.setenv("DATA_SOURCE", "csv")
    assert main(["read"]) == 1
    assert "CSV mode is read-only" in capsys.readouterr().out


def test_delete_cancellation_leaves_record_untouched(monkeypatch, capsys):
    identifier = str(ObjectId())
    repository = MagicMock()
    repository.read.return_value = [{"_id": identifier, "name": "River"}]
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    run_action(parser().parse_args(["--allow-writes", "delete", identifier]), repository)
    repository.delete.assert_not_called()
    assert "canceled" in capsys.readouterr().out


def test_delete_confirms_the_specific_record(monkeypatch):
    identifier = str(ObjectId())
    repository = MagicMock()
    repository.read.return_value = [{"_id": identifier}]
    monkeypatch.setattr("builtins.input", lambda prompt: "DELETE " + identifier)
    run_action(parser().parse_args(["--allow-writes", "delete", identifier]), repository)
    repository.delete.assert_called_once_with(identifier, confirmed=True)


def test_read_by_animal_id_builds_literal_query():
    repository = MagicMock()
    repository.read.return_value = []
    run_action(parser().parse_args(["read", "--animal-id", "M4-TEST"]), repository)
    repository.read.assert_called_once_with({"animal_id": "M4-TEST"})
