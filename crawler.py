from graphql_wrapper import GitHubGraphQlClient, Project, IssueType

import jira
import github

from loguru import logger as L

import trio


class Issue:
    def __init__(self, jira: jira.JIRA, issue_id: str):
        self._jira = jira
        self._issue_id = issue_id

        self._issue = self._jira.issue(issue_id)

    @property
    def issue_id(self) -> str:
        return self._issue_id

    @property
    def issue_name(self) -> str:
        return self._issue.fields.summary

    @property
    def issue(self) -> jira.Issue:
        return self._issue

class Epic(Issue):
    def __init__(self, jira: jira.JIRA, epic_id: str):
        super().__init__(jira, epic_id)

    @property
    def tasks(self) -> list[Issue]:
        return list(map(lambda issue_id: Issue(self._jira, issue_id),
            self._jira.search_issues(
                f'type=Task AND parent={self.issue_id} ORDER BY created ASC',
                maxResults=False
            )
        ))


class Crawler:
    MAX_PROJECTS = 25

    def __init__(self, jira_token: str, jira_project_id: str, github_token: str, github_repository: str):
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

        self._jira = jira.JIRA(
            server="https://naucto.atlassian.net",
            basic_auth=jira_token_tuple
        )

        L.info("Jira authenticated successfully")

        server_info = self._jira.server_info()
        L.debug("Jira instance is at {}", server_info["baseUrl"])

        self._jira_project: jira.Project | None = None

        for project in self._jira.projects():
            if project.key == jira_project_id:
                self._jira_project = project
                break

        if self._jira_project is None:
            raise ValueError(f"Jira project {jira_project_id} not found")

    def _transform_issue(self, target_issue_type: IssueType, issue: jira.Issue):
        pass

    def crawl(self):
        L.info("Initiated synchronization from Jira to GitHub")

        ql_target_repo = trio.run(self._github_graphql.get_repository, 
                        self._github_organization_name,
                        self._github_repository)

        ql_existing_projects = trio.run(ql_target_repo.get_projects)
        ql_target_project: Project | None = next(
            (project for project in ql_existing_projects \
                    if project.title == self._github_project_name),
            None
        )

        if ql_target_project is None:
            L.error("Target project {} not found, please create it", self._github_project_name)
            return

        ql_project_issue_types = trio.run(ql_target_repo.get_issue_types)
        L.debug("Found {} issue types in GitHub target project", len(ql_project_issue_types))
        ql_target_issue_type: IssueType | None = next(
            (issue_type for issue_type in ql_project_issue_types \
                    if issue_type.title == "Task"),
            None
        )

        if ql_target_issue_type is None:
            L.error("Target issue type 'Task' not found in GitHub project, something is wrong")
            return

        jira_tasks = list(map(
            lambda epic_id: Epic(self._jira, epic_id),
            self._jira.search_issues(
                f"project={str(self._jira_project)} AND type=Task ORDER BY created ASC",
                maxResults=False
            )
        ))

        ql_tasks = trio.run(ql_target_repo.get_issues)

        L.info("Updating target GitHub project with {} Jira tasks on {} ({} present)",
               len(jira_tasks), self._github_repository, len(ql_tasks))

        for jira_task in jira_tasks:
            L.debug("Processing Jira task {} ({})", jira_task.issue_id, jira_task.issue_name)
            self._transform_issue(ql_target_issue_type, jira_task.issue)
