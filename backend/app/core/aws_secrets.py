from __future__ import annotations

import json
from typing import Any


def _normalize_secret_value(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RuntimeError("AWS secrets payload must be a JSON object.")
    return parsed


def load_aws_runtime_settings(
    *,
    region: str,
    secrets_manager_secret_id: str | None,
    parameter_store_path: str | None,
) -> dict[str, Any]:
    if not secrets_manager_secret_id and not parameter_store_path:
        return {}

    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "AWS runtime secret loading is enabled but boto3 is not installed."
        ) from exc

    session = boto3.session.Session(region_name=region)
    loaded_settings: dict[str, Any] = {}

    if secrets_manager_secret_id:
        secrets_client = session.client("secretsmanager")
        secret_response = secrets_client.get_secret_value(SecretId=secrets_manager_secret_id)
        secret_string = secret_response.get("SecretString")
        if not secret_string:
            raise RuntimeError("Secrets Manager did not return a SecretString payload.")
        loaded_settings.update(_normalize_secret_value(secret_string))

    if parameter_store_path:
        ssm_client = session.client("ssm")
        next_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {
                "Path": parameter_store_path,
                "Recursive": True,
                "WithDecryption": True,
            }
            if next_token:
                kwargs["NextToken"] = next_token

            response = ssm_client.get_parameters_by_path(**kwargs)
            for parameter in response.get("Parameters", []):
                name = parameter["Name"].split("/")[-1]
                loaded_settings[name] = parameter["Value"]

            next_token = response.get("NextToken")
            if not next_token:
                break

    return loaded_settings
