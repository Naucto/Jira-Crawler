import json

from wrapper.jira import JiraUser, JiraIssueStatus
from wrapper.github import GitHubGraphQlClient, QlUser, QlIssueStatus


class BridgeMapping:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as file:
            mapping = json.load(file)

        self._mapping: dict[str, str] = {}

        if "mapping" not in mapping or not isinstance(mapping["mapping"], dict):
            raise ValueError("Bridge mapping configuration is missing 'mapping' key")

        for jira_user_id, github_user_id in mapping["mapping"].items():
            if not isinstance(jira_user_id, str) or not isinstance(github_user_id, str):
                raise ValueError("Bridge mapping configuration must have string keys and values")

            self._mapping[jira_user_id] = github_user_id

    async def map(self, ql_client: GitHubGraphQlClient, jira_user: JiraUser) -> QlUser | None:
        if jira_user.id not in self._mapping:
            return None

        github_user_id = self._mapping[jira_user.id]
        github_user = await ql_client.get_user(github_user_id)

        if github_user is None:
            raise ValueError(f"Github user with ID {github_user_id} not found")

        return github_user


class JiraIssueStatusMapping:
    @staticmethod
    def for_(status: JiraIssueStatus) -> QlIssueStatus:
        match status:
            case JiraIssueStatus.TODO:
                return QlIssueStatus.TODO
            case JiraIssueStatus.IN_PROGRESS | JiraIssueStatus.TO_REVIEW:
                return QlIssueStatus.IN_PROGRESS
            case JiraIssueStatus.DONE:
                return QlIssueStatus.DONE
