import httpx
from app.config import get_settings
from app.utils.logger import logger
from typing import Any


class GitHubClient:
    def __init__(self):
        settings = get_settings()
        self._token = settings.github_token
        self._base_url = "https://api.github.com"
        self._headers = {"Authorization": f"token {self._token}", "Accept": "application/vnd.github.v3+json"}

    async def get_recent_commits(self, owner: str = "", repo: str = "", per_page: int = 10) -> list[dict[str, Any]]:
        if not self._token:
            logger.warning("GitHub token not configured, returning empty commits list")
            return []

        if not owner or not repo:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/repos/{owner}/{repo}/commits",
                headers=self._headers,
                params={"per_page": per_page},
            )
            resp.raise_for_status()
            commits = resp.json()
            logger.debug(f"Fetched {len(commits)} recent commits from {owner}/{repo}")
            return commits

    async def get_commit_diff(self, owner: str, repo: str, commit_sha: str) -> str:
        if not self._token:
            return ""

        async with httpx.AsyncClient() as client:
            headers = {**self._headers, "Accept": "application/vnd.github.v3.diff"}
            resp = await client.get(
                f"{self._base_url}/repos/{owner}/{repo}/commits/{commit_sha}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.text
