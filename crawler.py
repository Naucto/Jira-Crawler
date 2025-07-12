from graphql_wrapper import GithubGraphQlClient, Project

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
        self._github_repository = github_repository

        self._github_rest = github.Github(
            login_or_token=github_token,
            auth=github.Auth.Token(github_token)
        )

        L.info("Github REST API authenticated successfully")

        self._github_graphql = GithubGraphQlClient(github_token)

        L.info("Github GraphQL API authenticated successfully")

        github_repository_set: list[str] = github_repository.split("/")
        if len(github_repository_set) != 2:
            raise ValueError("Github repository is not in the correct format")

        (github_organization_name, github_repo_name) = tuple(github_repository_set[:2]) # type: ignore

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

    def _transform_issue(self, issue: jira.Issue):
        pass

    def crawl(self):
        L.info("Initiated synchronization from Jira to GitHub")

        jira_epics = map(
            lambda epic_id: Epic(self._jira, epic_id),
            self._jira.search_issues(
                f"project={str(self._jira_project)} AND type=Epic ORDER BY created ASC",
                maxResults=False
            )
        )

        owner, repo_name = self._github_repository.split("/")

        repo = trio.run(self._github_graphql.get_repository, owner, repo_name)
        existing_projects = trio.run(repo.get_projects)

        L.debug("{} GitHub projects found on target repo", len(existing_projects))

        for epic in jira_epics:
            L.debug("Epic {} ({}) found with {} tasks", epic.issue_id, epic.issue_name, len(epic.tasks))

            project: Project | None = next(
                (p for p in existing_projects if p.title == epic.issue_name),
                None
            )

            if project is not None:
                L.info("Project {} found, updating it", epic.issue_name)
            else:
                L.info("Project {} not found, creating it", epic.issue_name)
                project = trio.run(repo.create_project, epic.issue_name)

            print(project)
