"""GitHub API 客户端封装。

基于 `httpx`，负责拉取提交 Diff、解析变更文件与行数统计，
并处理分页、限流（`X-RateLimit-*`）与鉴权。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Diff 文件头匹配：diff --git a/xxx b/xxx
_DIFF_FILE_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$")
# 新增/删除行匹配
_ADD_RE = re.compile(r"^\+[^+]")
_DEL_RE = re.compile(r"^-[^-]")
_HUNK_RE = re.compile(r"^@@ ")


class GitHubClientError(Exception):
    """GitHub 客户端异常基类。"""


class GitHubClient:
    """基于 httpx 的 GitHub REST API 客户端。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._headers: Dict[str, str] = {"Accept": "application/vnd.github.v3.diff"}
        if self.settings.github_token:
            self._headers["Authorization"] = f"token {self.settings.github_token}"

    def _is_available(self) -> bool:
        return bool(self.settings.github_token)

    def _check_rate_limit(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) == 0:
            reset = resp.headers.get("X-RateLimit-Reset")
            raise GitHubClientError(f"GitHub API 限流已达上限，重置时间：{reset}")

    def get_commit_diff(
        self, repo: str, commit_sha: str, timeout: float = 30.0
    ) -> Dict[str, Any]:
        """拉取单个提交的 Diff，并解析文件变更统计。

        Args:
            repo: 形如 `owner/name` 的仓库全名。
            commit_sha: 提交 SHA。

        Returns:
            `{"repo", "commit_sha", "diff_text", "files", "total_additions",
              "total_deletions"}`。
        """
        if not self._is_available():
            # 未配置 Token 时返回模拟数据，便于本地演示与测试。
            logger.warning("未配置 GITHUB_TOKEN，返回模拟 Diff。")
            return self._mock_diff(repo, commit_sha)

        url = f"{self.settings.github_api_base}/repos/{repo}/commits/{commit_sha}"
        try:
            with httpx.Client(headers=self._headers, timeout=timeout) as client:
                resp = client.get(url)
                self._check_rate_limit(resp)
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubClientError(f"GitHub API 请求失败：{exc}") from exc
        except httpx.RequestError as exc:
            raise GitHubClientError(f"GitHub API 网络错误：{exc}") from exc

        diff_text = resp.text
        return self._parse_diff(repo, commit_sha, diff_text)

    @staticmethod
    def _parse_diff(repo: str, commit_sha: str, diff_text: str) -> Dict[str, Any]:
        """解析 unified diff 文本，统计每个文件的增删行。"""
        files: List[Dict[str, Any]] = []
        current_file: Optional[Dict[str, Any]] = None
        total_add = total_del = 0

        for line in diff_text.splitlines():
            m = _DIFF_FILE_RE.match(line)
            if m:
                current_file = {
                    "filename": m.group(2),
                    "additions": 0,
                    "deletions": 0,
                    "language": GitHubClient._guess_language(m.group(2)),
                }
                files.append(current_file)
                continue
            if current_file is None or _HUNK_RE.match(line):
                continue
            if _ADD_RE.match(line):
                current_file["additions"] += 1
                total_add += 1
            elif _DEL_RE.match(line):
                current_file["deletions"] += 1
                total_del += 1

        return {
            "repo": repo,
            "commit_sha": commit_sha,
            "diff_text": diff_text,
            "files": files,
            "total_additions": total_add,
            "total_deletions": total_del,
        }

    @staticmethod
    def _guess_language(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
            "go": "go",
            "rs": "rust",
            "java": "java",
            "c": "c",
            "cpp": "cpp",
            "json": "json",
            "md": "markdown",
        }.get(ext, "text")

    @staticmethod
    def _mock_diff(repo: str, commit_sha: str) -> Dict[str, Any]:
        """未配置 Token 时的演示用模拟数据。"""
        sample = (
            "diff --git a/src/app.py b/src/app.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1,4 +1,6 @@\n"
            " def main():\n"
            "     data = []\n"
            "-    return data\n"
            "+    for i in range(100):\n"
            "+        data.append(i)\n"
            "+    return data\n"
            "diff --git a/README.md b/README.md\n"
            "--- a/README.md\n"
            "+++ b/README.md\n"
            "@@ -1 +1,2 @@\n"
            "-# Demo\n"
            "+# Demo\n"
            "+This is a sample diff.\n"
        )
        return GitHubClient._parse_diff(repo, commit_sha, sample)


def get_github_client() -> GitHubClient:
    return GitHubClient()
