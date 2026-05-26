"""
Curated test cases for evaluating Chief agent response quality.
Each test case has:
- A user message
- Mock context (what the agent would see)
- Expected routing (which agent should handle it)
- Quality criteria (what a good response must contain)
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TestCase:
    name: str
    user_message: str
    mock_context: str
    expected_agent: str
    must_contain: list[str]  # response must contain these (case-insensitive)
    must_not_contain: list[str]  # response must NOT contain these
    min_quality_score: int  # minimum acceptable quality score (0-100)


PULSE_TEST_CASES = [
    TestCase(
        name="recovery_status_with_data",
        user_message="What's my recovery today?",
        mock_context="""=== HEALTH CONTEXT (last 14 days) ===
Latest recovery: 72% (HRV: 45 ms, RHR: 52 bpm) recorded 2026-05-26
Sleep 7-day avg: 380 min, efficiency 84.0%
Workouts in last 14 days: 4
  - 2026-05-25: strain 14.2, 65 min, avg HR 148 bpm
RECOVERY TREND (7d): stable (avg 74.0%)""",
        expected_agent="Pulse",
        must_contain=["72", "recovery"],
        must_not_contain=["as an ai", "i don't have access", "i cannot"],
        min_quality_score=65,
    ),
    TestCase(
        name="training_recommendation_low_recovery",
        user_message="Should I do heavy squats today?",
        mock_context="""=== HEALTH CONTEXT (last 14 days) ===
Latest recovery: 38% (HRV: 28 ms, RHR: 64 bpm) recorded 2026-05-26
Sleep 7-day avg: 310 min, efficiency 71.0%
Workouts in last 14 days: 5""",
        expected_agent="Pulse",
        must_contain=["38", "not", "light"],  # should recommend against heavy squats
        must_not_contain=["as an ai", "i don't have access"],
        min_quality_score=60,
    ),
    TestCase(
        name="no_data_graceful",
        user_message="What's my HRV trend this week?",
        mock_context="No health data available yet. WHOOP not connected or not synced.",
        expected_agent="Pulse",
        must_contain=["connect", "whoop"],  # should suggest connecting WHOOP
        must_not_contain=["as an ai"],
        min_quality_score=40,
    ),
]

ECHO_TEST_CASES = [
    TestCase(
        name="stale_thread_summary",
        user_message="What emails need my attention?",
        mock_context="""=== COMMUNICATION CONTEXT ===
STALE THREADS (3 threads needing attention):
  [7d] "Thesis evaluation chapter feedback" from prof.westermann@tum.de via gmail
  [5d] "Re: EXIST application documents" from startup@exist.de via gmail
  [3d] "Invoice #2024-089" from accounting@client.com via gmail""",
        expected_agent="Echo",
        must_contain=["7", "thesis", "professor"],
        must_not_contain=["as an ai", "i sent", "i emailed"],
        min_quality_score=70,
    ),
    TestCase(
        name="draft_not_send",
        user_message="Send a reply to my professor about the thesis",
        mock_context="""=== COMMUNICATION CONTEXT ===
STALE THREADS (1 threads needing attention):
  [7d] "Thesis evaluation chapter feedback" from prof.westermann@tum.de via gmail""",
        expected_agent="Echo",
        must_not_contain=["i sent", "i emailed", "email sent", "has been sent"],
        must_contain=["draft"],
        min_quality_score=55,
    ),
]

FORGE_TEST_CASES = [
    TestCase(
        name="commit_velocity_with_data",
        user_message="How are my GitHub projects going this week?",
        mock_context="""=== PROJECTS CONTEXT ===
ACTIVE PROJECTS (2):
  - ChiefAI (github_repo)
  - thesis-object-detection (github_repo), deadline 2026-07-15
COMMIT VELOCITY:
  This week: 12 commits across 2 repos
  Previous period: 8 commits
  Trend: +4 commits vs previous period
  Recent commits:
    [ChiefAI] feat: add proactive intelligence engine (2026-05-26)
    [thesis-object-detection] fix: evaluation metrics calculation (2026-05-25)""",
        expected_agent="Forge",
        must_contain=["12", "commits"],
        must_not_contain=["as an ai", "i don't have access"],
        min_quality_score=65,
    ),
]

ALL_TEST_CASES = PULSE_TEST_CASES + ECHO_TEST_CASES + FORGE_TEST_CASES
