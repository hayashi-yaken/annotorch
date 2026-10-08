import pytest

from annotorch.errors import (
    AnnotorchError,
    AnswerValidationError,
    ConflictError,
    InvalidInputError,
    ItemFileMissingError,
    ItemsInUseError,
    NotADatasetError,
    NotFoundError,
    OutputExistsError,
    SchemaVersionError,
    WorkspaceError,
)


@pytest.mark.parametrize("cls, parents", [
    (NotFoundError, (AnnotorchError, LookupError)),
    (InvalidInputError, (AnnotorchError, ValueError)),
    (ConflictError, (AnnotorchError,)),
    (WorkspaceError, (AnnotorchError,)),
    (AnswerValidationError, (InvalidInputError, ValueError)),
    (ItemsInUseError, (ConflictError,)),
    (OutputExistsError, (ConflictError, FileExistsError)),
    (SchemaVersionError, (WorkspaceError,)),
    (ItemFileMissingError, (WorkspaceError,)),
    (NotADatasetError, (InvalidInputError, FileNotFoundError)),
])
def test_hierarchy(cls, parents):
    for parent in parents:
        assert issubclass(cls, parent)


def test_workspace_error_is_not_a_client_error():
    assert not issubclass(WorkspaceError, (NotFoundError, InvalidInputError, ConflictError))
