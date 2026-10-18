from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure, OperationFailure
import pytest

from data_access.mongo_repository import MongoAnimalRepository, RepositoryError, RESCUE_INDEX_KEYS


@pytest.fixture
def repository():
    with patch("data_access.mongo_repository.MongoClient") as factory:
        repository = MongoAnimalRepository("mongodb://localhost", "test", "animals", allow_writes=True)
        yield repository
        repository.close()
        factory.return_value.close.assert_called_once()


def test_create_returns_id_without_mutating_input(repository, animal):
    identifier = ObjectId()
    repository._collection.insert_one.return_value.inserted_id = identifier
    assert repository.create(animal) == str(identifier)
    repository._collection.insert_one.assert_called_once_with(animal)
    assert "_id" not in animal


def test_update_only_targets_one_document_and_sets_validated_fields(repository):
    identifier = ObjectId()
    repository._collection.update_one.return_value.matched_count = 1
    assert repository.update(str(identifier), {"name": "Changed"}) is True
    repository._collection.update_one.assert_called_once_with({"_id": identifier}, {"$set": {"name": "Changed"}})
    repository._collection.update_one.return_value.matched_count = 0
    assert repository.update(identifier, {"name": "Missing"}) is False


def test_delete_requires_exact_confirmation_and_id(repository):
    identifier = ObjectId()
    for confirmation in (False, None, "yes", 1):
        with pytest.raises(ValueError):
            repository.delete(identifier, confirmed=confirmation)
    with pytest.raises(ValueError):
        repository.delete({}, confirmed=True)
    repository._collection.delete_one.assert_not_called()
    repository._collection.delete_one.return_value.deleted_count = 1
    assert repository.delete(str(identifier), confirmed=True) is True
    repository._collection.delete_one.assert_called_once_with({"_id": identifier})


def test_writes_default_to_disabled(animal):
    with patch("data_access.mongo_repository.MongoClient"):
        repository = MongoAnimalRepository("mongodb://localhost", "test", "animals")
        for action in (
            lambda: repository.create(animal),
            lambda: repository.update(ObjectId(), {"name": "Changed"}),
            lambda: repository.delete(ObjectId(), confirmed=True),
            repository.ensure_indexes,
        ):
            with pytest.raises(ValueError, match="disabled"):
                action()
        repository._collection.insert_one.assert_not_called()
        repository.close()


def test_invalid_changes_never_reach_database(repository):
    with pytest.raises(ValueError):
        repository.update(ObjectId(), {"$set": {"name": "Changed"}})
    repository._collection.update_one.assert_not_called()


def test_read_uses_stable_id_order(repository):
    repository._collection.find.return_value.sort.return_value = [{"name": "River"}]
    assert repository.read({"name": "River"}) == [{"name": "River"}]
    repository._collection.find.return_value.sort.assert_called_once_with("_id", 1)


def test_indexes_use_equality_fields_before_age_range(repository):
    repository.ensure_indexes()
    repository._collection.create_index.assert_any_call(RESCUE_INDEX_KEYS, name="rescue_lookup")
    repository._collection.create_index.assert_any_call("animal_id", name="animal_id_lookup")


@pytest.mark.parametrize("operation", ["read", "create", "update", "delete", "ensure_indexes", "explain"])
def test_database_errors_do_not_expose_details(repository, animal, operation):
    secret = "mongodb://private:password@server"
    failure = OperationFailure(secret)
    collection = repository._collection
    for method in ("find", "insert_one", "update_one", "delete_one", "create_index"):
        getattr(collection, method).side_effect = failure
    collection.database.command.side_effect = failure
    arguments = {
        "read": (), "create": (animal,), "update": (ObjectId(), {"name": "Changed"}),
        "delete": (ObjectId(),), "ensure_indexes": (), "explain": (),
    }
    kwargs = {"confirmed": True} if operation == "delete" else {}
    with pytest.raises(RepositoryError) as caught:
        getattr(repository, operation)(*arguments[operation], **kwargs)
    assert secret not in str(caught.value)


def test_failed_connection_is_closed_and_message_is_safe():
    with patch("data_access.mongo_repository.MongoClient") as factory:
        factory.return_value.admin.command.side_effect = ConnectionFailure("secret")
        with pytest.raises(RepositoryError, match="Unable to connect") as caught:
            MongoAnimalRepository("mongodb://localhost", "test", "animals")
        assert "secret" not in str(caught.value)
        factory.return_value.close.assert_called_once()
