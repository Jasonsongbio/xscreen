"""Tests for LLMClient (mocked, no real API calls)."""
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.llm_client import LLMClient


def test_init_with_provider_model():
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    assert client.model == "deepseek-chat"
    assert client.provider == "deepseek"


def test_complete_json_parses_valid_array(mocker):
    mock_response = '[{"candidate": "NPF", "core_name": "NPF"}]'
    mocker.patch("src.llm_client.litellm.completion", return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_response))]
    ))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    result = client.complete_json(system="sys", user="usr")
    assert isinstance(result, list)
    assert result[0]["candidate"] == "NPF"


def test_complete_json_parses_dict_wrapped_in_list(mocker):
    """Some models return a single dict instead of array; should wrap in list."""
    mock_response = '{"candidate": "NPF", "core_name": "NPF"}'
    mocker.patch("src.llm_client.litellm.completion", return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_response))]
    ))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    result = client.complete_json(system="sys", user="usr")
    assert len(result) == 1
    assert result[0]["candidate"] == "NPF"


def test_complete_json_strips_markdown_code_fence(mocker):
    mock_response = '```json\n[{"candidate": "X", "core_name": "X"}]\n```'
    mocker.patch("src.llm_client.litellm.completion", return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_response))]
    ))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    result = client.complete_json(system="sys", user="usr")
    assert len(result) == 1


def test_complete_json_retries_on_invalid_then_succeeds(mocker):
    bad_then_good = [
        MagicMock(choices=[MagicMock(message=MagicMock(content="not json"))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content='[{"candidate":"X","core_name":"X"}]'))]),
    ]
    mocker.patch("src.llm_client.litellm.completion", side_effect=bad_then_good)
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake", max_retries=3)
    result = client.complete_json(system="sys", user="usr")
    assert len(result) == 1


def test_complete_json_returns_empty_after_max_retries(mocker):
    mocker.patch("src.llm_client.litellm.completion", return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="always bad"))]
    ))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake", max_retries=2)
    result = client.complete_json(system="sys", user="usr")
    assert result == []


def test_litellm_model_string_prefix():
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    assert client._litellm_model_string() == "deepseek/deepseek-chat"

    client2 = LLMClient(provider="anthropic", model="claude-sonnet-4-6", api_key="fake")
    assert client2._litellm_model_string() == "claude/claude-sonnet-4-6"

    # Already prefixed should not double-prefix
    client3 = LLMClient(provider="deepseek", model="deepseek/deepseek-chat", api_key="fake")
    assert client3._litellm_model_string() == "deepseek/deepseek-chat"


def test_complete_json_handles_api_exception(mocker):
    mocker.patch("src.llm_client.litellm.completion", side_effect=Exception("API timeout"))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake", max_retries=2)
    result = client.complete_json(system="sys", user="usr")
    assert result == []
