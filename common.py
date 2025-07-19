import json

from wrapper.jira import JiraUser
from wrapper.github import GitHubGraphQlClient, QlUser


class BridgeMapping:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as file:
            mapping = json.load(file)

        self._mapping: dict[str, str] = {}

        if "mapping" not in mapping or not isinstance(mapping["mapping"], dict):
            raise ValueError("Bridge mapping configuration is missing 'mapping' key")

        for user_email, github_user_id in mapping["mapping"].items():
            if not isinstance(user_email, str) or not isinstance(github_user_id, str):
                raise ValueError("Bridge mapping configuration must have string keys and values")

            self._mapping[user_email] = github_user_id

    def map(self, ql_client: GitHubGraphQlClient, jira_user: JiraUser) -> QlUser | None:
        if jira_user.email not in self._mapping:
            return None

        github_user_id = self._mapping[jira_user.email]
        github_user = ql_client.get_user(github_user_id)

        if github_user is None:
            raise ValueError(f"Github user with ID {github_user_id} not found")
