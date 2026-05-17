"""Tests for Claude Code CLI configuration integrity.

Validates that the Claude Code CLI setup — CLAUDE.md files, settings,
and skill definitions — is correctly structured for this project.

Generated with Claude Code CLI.
"""

import json
from pathlib import Path

import pytest

# Project root is two levels above this file (backend/tests/ -> backend/ -> root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
CLAUDE_DIR = PROJECT_ROOT / ".claude"

VALID_HOOK_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
    "Notification",
    "UserPromptSubmit",
}

VALID_HOOK_HANDLER_TYPES = {"command", "http", "mcp_tool", "prompt", "agent"}


# ---------------------------------------------------------------------------
# CLAUDE.md files
# ---------------------------------------------------------------------------


class TestClaudeMdFiles:
    """CLAUDE.md files exist at expected locations and contain required sections."""

    def test_root_claude_md_exists(self):
        assert (PROJECT_ROOT / "CLAUDE.md").is_file()

    def test_backend_claude_md_exists(self):
        assert (BACKEND_ROOT / "CLAUDE.md").is_file()

    def test_frontend_claude_md_exists(self):
        assert (PROJECT_ROOT / "frontend" / "CLAUDE.md").is_file()

    def test_root_claude_md_has_project_overview(self):
        content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Project Overview" in content

    def test_root_claude_md_has_local_development(self):
        content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Local Development" in content

    def test_root_claude_md_has_git_conventions(self):
        content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Git conventions" in content

    def test_root_claude_md_references_backend_claude(self):
        """Root CLAUDE.md must point to backend/CLAUDE.md so Claude Code loads it."""
        content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "backend/CLAUDE.md" in content

    def test_root_claude_md_size_is_concise(self):
        """Keep root CLAUDE.md under 200 lines — longer files risk being truncated in context."""
        lines = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
        assert len(lines) < 200, f"CLAUDE.md has {len(lines)} lines; keep under 200"

    def test_backend_claude_md_has_commands_section(self):
        content = (BACKEND_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Commands" in content

    def test_backend_claude_md_has_testing_section(self):
        content = (BACKEND_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Testing" in content

    def test_backend_claude_md_has_stack_section(self):
        content = (BACKEND_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Stack" in content


# ---------------------------------------------------------------------------
# settings.local.json
# ---------------------------------------------------------------------------


class TestSettingsJson:
    """Claude Code settings.local.json has a valid, parseable structure."""

    @pytest.fixture(scope="class")
    def settings_path(self):
        return CLAUDE_DIR / "settings.local.json"

    @pytest.fixture(scope="class")
    def settings_data(self, settings_path):
        return json.loads(settings_path.read_text(encoding="utf-8"))

    def test_settings_file_exists(self, settings_path):
        assert settings_path.is_file()

    def test_settings_is_valid_json(self, settings_path):
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_settings_has_no_unknown_top_level_keys(self, settings_data):
        known_keys = {
            "permissions", "hooks", "env",
            "includeCoAuthoredBy", "model", "cleanupPeriodDays",
        }
        unknown = set(settings_data.keys()) - known_keys
        assert not unknown, f"Unknown top-level keys: {unknown}"

    def test_permissions_allow_is_list(self, settings_data):
        if "permissions" not in settings_data:
            pytest.skip("No permissions configured")
        perms = settings_data["permissions"]
        if "allow" in perms:
            assert isinstance(perms["allow"], list)

    def test_permissions_deny_is_list_if_present(self, settings_data):
        if "permissions" not in settings_data:
            pytest.skip("No permissions configured")
        perms = settings_data["permissions"]
        if "deny" in perms:
            assert isinstance(perms["deny"], list)

    def test_hooks_have_valid_event_names(self, settings_data):
        if "hooks" not in settings_data:
            pytest.skip("No hooks configured")
        for entry in settings_data["hooks"]:
            assert "event" in entry, "Hook entry missing 'event' field"
            assert entry["event"] in VALID_HOOK_EVENTS, (
                f"Unknown hook event: {entry['event']}"
            )

    def test_hooks_handlers_have_valid_types(self, settings_data):
        if "hooks" not in settings_data:
            pytest.skip("No hooks configured")
        for entry in settings_data["hooks"]:
            for handler in entry.get("hooks", []):
                assert "type" in handler, "Handler missing 'type' field"
                assert handler["type"] in VALID_HOOK_HANDLER_TYPES, (
                    f"Unknown handler type: {handler['type']}"
                )


# ---------------------------------------------------------------------------
# Backend skills
# ---------------------------------------------------------------------------

_BACKEND_SKILLS = [
    "python-executor",
    "fastapi-python",
    "fastapi-templates",
    "python-testing-patterns",
]


class TestBackendSkills:
    """Backend .claude/skills/ has valid, well-formed skill definitions."""

    @pytest.fixture(scope="class")
    def skills_dir(self):
        return BACKEND_ROOT / ".claude" / "skills"

    def test_skills_directory_exists(self, skills_dir):
        assert skills_dir.is_dir()

    @pytest.mark.parametrize("skill", _BACKEND_SKILLS)
    def test_skill_directory_exists(self, skills_dir, skill):
        assert (skills_dir / skill).is_dir()

    @pytest.mark.parametrize("skill", _BACKEND_SKILLS)
    def test_skill_has_skill_md(self, skills_dir, skill):
        assert (skills_dir / skill / "SKILL.md").is_file()

    @pytest.mark.parametrize("skill", _BACKEND_SKILLS)
    def test_skill_md_opens_with_frontmatter(self, skills_dir, skill):
        content = (skills_dir / skill / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---"), f"{skill}/SKILL.md must begin with '---' frontmatter"

    @pytest.mark.parametrize("skill", _BACKEND_SKILLS)
    def test_skill_md_has_name_field(self, skills_dir, skill):
        content = (skills_dir / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "name:" in content

    @pytest.mark.parametrize("skill", _BACKEND_SKILLS)
    def test_skill_md_has_description_field(self, skills_dir, skill):
        content = (skills_dir / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "description:" in content

    @pytest.mark.parametrize("skill", _BACKEND_SKILLS)
    def test_skill_md_closes_frontmatter(self, skills_dir, skill):
        content = (skills_dir / skill / "SKILL.md").read_text(encoding="utf-8")
        # Must have at least 3 segments: before opening ---, frontmatter, body
        parts = content.split("---")
        assert len(parts) >= 3, f"{skill}/SKILL.md frontmatter is not closed with '---'"


# ---------------------------------------------------------------------------
# Project conventions enforced by Claude Code
# ---------------------------------------------------------------------------


class TestProjectConventions:
    """Claude Code CLI conventions are followed in the project structure."""

    def test_conventional_commit_types_documented(self):
        content = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for commit_type in ("feat", "fix", "docs", "test", "chore"):
            assert commit_type in content, (
                f"Commit type '{commit_type}' not documented in CLAUDE.md"
            )

    def test_gitignore_exists_at_root(self):
        assert (PROJECT_ROOT / ".gitignore").is_file()

    def test_env_example_exists(self):
        """Secrets are documented via .env.example, never committed."""
        assert (BACKEND_ROOT / ".env.example").is_file()

    def test_env_example_documents_secret_key(self):
        content = (BACKEND_ROOT / ".env.example").read_text(encoding="utf-8")
        assert "SECRET_KEY" in content

    def test_env_example_documents_redis_url(self):
        content = (BACKEND_ROOT / ".env.example").read_text(encoding="utf-8")
        assert "REDIS_URL" in content

    def test_env_example_documents_rate_limit_tiers(self):
        content = (BACKEND_ROOT / ".env.example").read_text(encoding="utf-8")
        assert "RATE_LIMIT_LLM_PER_MINUTE" in content
        assert "RATE_LIMIT_IMAGE_PER_MINUTE" in content

    def test_claude_dir_exists(self):
        assert CLAUDE_DIR.is_dir()