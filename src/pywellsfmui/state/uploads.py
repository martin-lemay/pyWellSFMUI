"""Safety checks for JSON files uploaded by users."""

import json
from typing import Any


def _find_file_reference(obj: Any) -> str | None:  # noqa: ANN401
    """Return the first ``url`` file reference found in a JSON object."""
    if isinstance(obj, dict):
        url = obj.get("url")
        if isinstance(url, str):
            return url
        values = list(obj.values())
    elif isinstance(obj, list):
        values = obj
    else:
        return None
    for value in values:
        found = _find_file_reference(value)
        if found is not None:
            return found
    return None


def load_uploaded_json(data: bytes | str) -> Any:  # noqa: ANN401
    """Parse an uploaded JSON file, rejecting references to other files.

    Uploads are processed on the server, where a ``url`` reference would be
    resolved against the server file system. Uploaded files must therefore
    be self-contained (all data inline).

    Args:
        data: raw content of the uploaded file.

    Returns:
        The parsed JSON object.

    Raises:
        ValueError: if the content is not valid JSON or contains a ``url``
            file reference.
    """
    obj = json.loads(data)
    url = _find_file_reference(obj)
    if url is not None:
        raise ValueError(
            "Uploaded files must be self-contained: replace the reference "
            f"to '{url}' by inline data."
        )
    return obj
