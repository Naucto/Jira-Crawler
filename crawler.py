from wrapper.github import GitHubGraphQlClient, QlUser, QlProject, QlIssueType, QlIssue
from wrapper.jira import JiraClient, JiraUser, JiraProject, JiraEpic, JiraIssue
from common import BridgeMapping

import github

from loguru import logger as L


class Crawler:
    MAX_PROJECTS = 25

    def __init__(self, jira_token: str, jira_project_id: str, github_token: str,
                 github_repository: str, bridge_mapping: BridgeMapping):
        self._github_rest = github.Github(
            login_or_token=github_token,
            auth=github.Auth.Token(github_token)
        )

        L.info("Github REST API authenticated successfully")

        self._github_graphql = GitHubGraphQlClient(github_token)

        L.info("Github GraphQL API authenticated successfully")

        github_repository_set: list[str] = github_repository.split("/")
        if len(github_repository_set) != 3:
            raise ValueError("Github repository is not in the correct format")

        (
                github_organization_name,
                github_repo_name,
                github_project_name
        ) = tuple(github_repository_set[:3]) # type: ignore

        self._github_organization_name = github_organization_name
        self._github_repository = github_repo_name
        self._github_project_name = github_project_name

        github_organization = self._github_rest.get_organization(github_organization_name)
        L.debug("Github organization {} found", github_organization.login)

        self._github_rest_repo = github_organization.get_repo(github_repo_name)
        L.debug("Github repository {} found", self._github_rest_repo.name)

        jira_token_set: list[str] = jira_token.split("/")

        if len(jira_token_set) != 2:
            raise ValueError("Jira token is not in the correct format")

        jira_token_tuple: tuple[str, str] = tuple(jira_token_set[:2]) # type: ignore

        self._jira = JiraClient("https://naucto.atlassian.net", jira_token_tuple)

        L.info("Jira authenticated successfully")
        L.debug("Jira instance is at {}", self._jira.base_url)

        jira_project = self._jira.get_project(jira_project_id)

        if jira_project is None:
            raise ValueError(f"Jira project {jira_project_id} not found")

        self._jira_project: JiraProject = jira_project

        self._bridge_mapping = bridge_mapping

    async def _transform_issue(self, ql_issue: QlIssue, jira_issue: JiraIssue):
        source_user: JiraUser | None = jira_issue.assignee
        mapped_user: QlUser | None = None

        if source_user is not None:
            mapped_user = self._bridge_mapping.map(self._github_graphql, source_user)

            if mapped_user:
                L.trace("Found mapped user {} for Jira user {}",
                        mapped_user.login, source_user.email)

                ql_issue.assigned_users = [mapped_user]

    async def crawl(self):
        L.info("Initiated synchronization from Jira to GitHub")

        ql_target_repo = await self._github_graphql.get_repository(
            self._github_organization_name,
            self._github_repository
        )

        ql_existing_projects = await ql_target_repo.get_projects()
        ql_target_project: QlProject | None = next(
            (project for project in ql_existing_projects \
                    if project.title == self._github_project_name),
            None
        )

        if ql_target_project is None:
            raise ValueError(f"Target project {self._github_project_name} not found, please create it")

        ql_project_issue_types = await ql_target_repo.get_issue_types()
        L.debug("Found {} issue types in GitHub target project", len(ql_project_issue_types))
        ql_target_issue_type: QlIssueType | None = next(
            (issue_type for issue_type in ql_project_issue_types \
                    if issue_type.title == "Task"),
            None
        )

        if ql_target_issue_type is None:
            L.error("Target issue type 'Task' not found in GitHub project, something is wrong")
            return

        jira_issues = self._jira_project.get_issues()

        ql_issues = await ql_target_repo.get_issues()
        ql_issues = {issue.title: issue for issue in ql_issues}

        L.info("Updating target GitHub project with {} Jira tasks on {} ({} present)",
               len(jira_issues), self._github_repository, len(ql_issues))

        for jira_issue in jira_issues:
            trsf_issue_name = f"[{jira_issue.id}] {jira_issue.name}"
            ql_issue = ql_issues.get(trsf_issue_name)

            if ql_issue is None:
                L.debug("Creating new GitHub issue for Jira task {} ({})", jira_issue.id, jira_issue.name)
                ql_issue = await ql_target_repo.create_issue(
                    ql_target_issue_type,
                    trsf_issue_name,
                    jira_issue.description
                )

                continue

            L.debug("Processing Jira task {} ({})", jira_issue.id, jira_issue.name)
            await self._transform_issue(ql_issue, jira_issue)
