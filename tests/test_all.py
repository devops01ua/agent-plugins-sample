import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from acme_mcp import export, install  # noqa: E402
from acme_mcp.model import load_plugins  # noqa: E402

PLUGIN_DIR = REPO / "plugins" / "devops" / "acme-platform"
ENV = {
    "ACME_ACME_PLATFORM_PROD_TOKEN": "prod-secret",
    "ACME_ACME_PLATFORM_TEST_TOKEN": "test-secret",
}


class ExportTest(unittest.TestCase):
    def test_committed_manifests_are_fresh(self):
        self.assertEqual(export.export(REPO, check=True), [])

    def test_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(REPO, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            generated = copy / "plugins" / "devops" / "acme-platform" / "mcp.json"
            generated.write_text(generated.read_text().replace("gitops-prod", "edited-by-hand"))
            stale = export.export(copy, check=True)
            self.assertEqual([p.name for p in stale], ["mcp.json"])

    def test_no_user_config_reference_survives(self):
        for path, text in export.all_files(REPO).items():
            if path.name in ("mcp.json", "codex.mcp.json"):
                self.assertNotIn("user_config", text, path)
                self.assertIn("${ACME_ACME_PLATFORM_PROD_TOKEN}", text, path)


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["ACME_HOME"] = self.tmp.name
        self.addCleanup(os.environ.pop, "ACME_HOME", None)
        self.home = Path(self.tmp.name)
        self.plugin = load_plugins(REPO)[0]

    def run_install(self, tool):
        return install.install(self.plugin, tool, interactive=False, environ=ENV)

    def check_server(self, server):
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["args"], [str(PLUGIN_DIR / "server" / "gitops_mcp.py")])
        self.assertEqual(server["env"]["GITOPS_API_TOKEN"], "prod-secret")
        self.assertEqual(server["env"]["GITOPS_BASE_URL"], "https://gitops.example.com")

    def test_json_tools_keep_other_servers(self):
        for tool in ("kiro", "antigravity"):
            config = self.home / install.TOOLS[tool]["config"]
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"mcpServers": {"mine": {"command": "x"}}}))
            self.run_install(tool)
            servers = json.loads(config.read_text())["mcpServers"]
            self.assertEqual(sorted(servers), ["gitops-prod", "gitops-test", "mine"])
            self.check_server(servers["gitops-prod"])
            self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)

    def test_codex_toml_is_valid_and_idempotent(self):
        config = self.home / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "x"\n\n[mcp_servers.mine]\ncommand = "x"\n')
        self.run_install("codex")
        first = config.read_text()
        self.run_install("codex")
        self.assertEqual(config.read_text(), first)
        data = tomllib.loads(first)
        self.assertEqual(data["model"], "x")
        self.assertEqual(sorted(data["mcp_servers"]), ["gitops-prod", "gitops-test", "mine"])
        self.check_server(data["mcp_servers"]["gitops-prod"])
        self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)

    def test_skills_are_linked_or_copied(self):
        self.run_install("codex")
        linked = self.home / ".agents" / "skills" / "rollout-check"
        self.assertTrue(linked.is_symlink())
        self.run_install("kiro")
        copied = self.home / ".kiro" / "skills" / "rollout-check"
        self.assertFalse(copied.is_symlink())
        self.assertTrue((copied / "SKILL.md").is_file())


class ServerTest(unittest.TestCase):
    def talk(self, env_name, messages):
        env = {**os.environ, "GITOPS_ENV": env_name, "GITOPS_API_TOKEN": "prod-secret",
               "GITOPS_BASE_URL": "https://gitops.example.com"}
        out = subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "server" / "gitops_mcp.py")],
            input="\n".join(json.dumps(m) for m in messages) + "\n",
            capture_output=True, text=True, env=env, timeout=10,
        ).stdout
        return [json.loads(line) for line in out.splitlines()], out

    def test_handshake_and_tools(self):
        call = lambda i, name, args=None: {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                                           "params": {"name": name, "arguments": args or {}}}
        replies, raw = self.talk("prod", [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            call(3, "get_application", {"name": "payments"}),
            call(4, "whoami"),
            call(5, "get_application", {"name": "nope"}),
            {"jsonrpc": "2.0", "id": 6, "method": "deploy/apply"},
        ])
        self.assertEqual([r["id"] for r in replies], [1, 2, 3, 4, 5, 6])
        self.assertEqual(replies[0]["result"]["serverInfo"]["name"], "acme-gitops-prod")
        self.assertEqual(len(replies[1]["result"]["tools"]), 4)
        app = json.loads(replies[2]["result"]["content"][0]["text"])
        self.assertEqual((app["sync"], app["live_revision"]), ("OutOfSync", "5d2a8c0"))
        self.assertEqual(json.loads(replies[3]["result"]["content"][0]["text"])["token"], "set")
        self.assertTrue(replies[4]["result"]["isError"])
        self.assertEqual(replies[5]["error"]["code"], -32601)
        self.assertNotIn("prod-secret", raw)  # the token is never echoed


class HookTest(unittest.TestCase):
    def fire(self, tmp, transcript_text, session="s1"):
        transcript = Path(tmp) / "t.jsonl"
        transcript.write_text(transcript_text)
        event = {"session_id": session, "transcript_path": str(transcript), "stop_hook_active": False}
        return subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "hooks" / "remind_notes.py")],
            input=json.dumps(event), capture_output=True, text=True, timeout=10,
            env={**os.environ, "CLAUDE_PLUGIN_DATA": tmp},
        )

    def test_reminds_once_and_only_after_gitops_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            quiet = self.fire(tmp, "edited a README", session="other")
            self.assertEqual((quiet.returncode, quiet.stdout), (0, ""))
            first = self.fire(tmp, "mcp__plugin_acme-platform_gitops-prod__get_application")
            self.assertIn("systemMessage", json.loads(first.stdout))
            second = self.fire(tmp, "mcp__plugin_acme-platform_gitops-prod__get_application")
            self.assertEqual((second.returncode, second.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
