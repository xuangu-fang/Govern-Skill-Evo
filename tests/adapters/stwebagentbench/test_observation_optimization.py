from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from browsergym.core.action.base import execute_python_code

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = PROJECT_ROOT / "external/ST-WebAgentBench"
sys.path.insert(0, str(BENCHMARK_ROOT))

import st_bench_example
from stwebagentbench.browser_env import custom_env


class _Page:
    url = "http://suitecrm.test/index.php"


class _Context:
    def __init__(self, page: _Page) -> None:
        self.pages = [page]


class _Chat:
    messages = [{"role": "user", "message": "Open the contact."}]


class _Task:
    @staticmethod
    def get_policies() -> list[dict]:
        return [{"policy_template_id": "confirm_before_update"}]


def test_common_action_set_registers_report_infeasible() -> None:
    action_set = st_bench_example.get_action_set(multiaction=False)

    assert "report_infeasible" in action_set.action_set
    generated_code = action_set.to_python_code(
        'report_infeasible("The requested operation is not permitted.")'
    )
    assert generated_code.rstrip().endswith(
        "report_infeasible('The requested operation is not permitted.')"
    )
    reported_reasons = []
    execute_python_code(
        generated_code,
        page=None,
        send_message_to_user=lambda message: None,
        report_infeasible_instructions=reported_reasons.append,
    )
    assert reported_reasons == ["The requested operation is not permitted."]


def test_get_obs_uses_schema_valid_placeholders_without_expensive_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = custom_env.BrowserEnv(task_entrypoint=lambda seed=None: None)
    page = _Page()
    env.page = page
    env.context = _Context(page)
    env.chat = _Chat()
    env.task = _Task()
    env.last_action = ""
    env.last_action_error = ""
    env.start_time = 0.0

    monkeypatch.setattr(custom_env, "_pre_extract", lambda page, tags: None)
    monkeypatch.setattr(custom_env, "_post_extract", lambda page: None)
    monkeypatch.setattr(custom_env, "extract_dom_snapshot", lambda page: {"dom": 1})
    monkeypatch.setattr(
        custom_env, "extract_merged_axtree", lambda page: {"axtree": 1}
    )
    monkeypatch.setattr(
        custom_env, "extract_focused_element_bid", lambda page: "focused"
    )
    monkeypatch.setattr(
        custom_env, "extract_dom_extra_properties", lambda dom: {"extra": 1}
    )
    monkeypatch.setattr(
        custom_env,
        "extract_screenshot",
        lambda page: pytest.fail("real screenshot extraction must not run"),
        raising=False,
    )
    monkeypatch.setattr(
        env,
        "read_webpage_content",
        lambda: pytest.fail("real page text extraction must not run"),
    )

    obs = env._get_obs()

    assert env.observation_space["screenshot"].contains(obs["screenshot"])
    assert env.observation_space["read_page"].contains(obs["read_page"])
    assert obs["screenshot"].shape == (0, 0, 3)
    assert obs["screenshot"].dtype == np.uint8
    assert obs["read_page"] == ()
    assert obs["dom_object"] == {"dom": 1}
    assert obs["axtree_object"] == {"axtree": 1}
    assert obs["extra_element_properties"] == {"extra": 1}
    assert obs["focused_element_bid"] == "focused"
    assert obs["url"] == page.url
    assert obs["goal"] == "Open the contact."
    assert obs["policies"] == _Task.get_policies()


def test_demo_agent_preprocessed_observation_schema_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        st_bench_example, "flatten_axtree_to_str", lambda value: "AXTREE"
    )
    raw = {
        "policies": [{"id": "policy"}],
        "goal": "Open the contact.",
        "chat_messages": [{"role": "user", "message": "Open it."}],
        "axtree_object": {"nodes": []},
        "url": "http://suitecrm.test/index.php",
        "screenshot": np.empty((0, 0, 3), dtype=np.uint8),
        "read_page": (),
    }

    processed = st_bench_example.DemoAgent.obs_preprocessor(object(), raw)

    assert processed == {
        "policies": raw["policies"],
        "goal": raw["goal"],
        "chat_messages": raw["chat_messages"],
        "axtree_txt": "AXTREE",
        "url": raw["url"],
    }
