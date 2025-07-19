import jira

from typing import Tuple


class JiraUser:
    def __init__(self, user: jira.User):
        self._user = user

    @property
    def id(self) -> str:
        return self._user.accountId

    @property
    def name(self) -> str:
        return self._user.displayName

    @property
    def email(self) -> str:
        return self._user.emailAddress


class JiraIssue:
    def __init__(self, jira: jira.JIRA, issue_id: str):
        self._jira = jira
        self._id = issue_id

        self._issue = self._jira.issue(issue_id)

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._issue.fields.summary

    @property
    def description(self) -> str:
        return self._issue.fields.description or ""

    @property
    def issue(self) -> jira.Issue:
        return self._issue

    @property
    def assignee(self) -> JiraUser | None:
        if self._issue.fields.assignee is None:
            return None

        return JiraUser(
            self._jira.user(id=self._issue.fields.assignee.accountId)
        )


class JiraEpic(JiraIssue):
    def __init__(self, jira: jira.JIRA, epic_id: str):
        super().__init__(jira, epic_id)

    @property
    def tasks(self) -> list[JiraIssue]:
        return list(map(lambda issue_id: JiraIssue(self._jira, issue_id),
            self._jira.search_issues(
                f'type=Task AND parent={self.id} ORDER BY created ASC',
                maxResults=False
            )
        ))


class JiraProject:
    def __init__(self, client: "JiraClient", project: jira.Project):
        self._client = client
        self._project = project

    def get_issues(self) -> list[JiraIssue]:
        return list(map(lambda issue_id: JiraIssue(self._client._client, issue_id),
            self._client._client.search_issues(
                f'project={self.id} AND type=Task ORDER BY created ASC',
                maxResults=False
            )
        ))

    @property
    def id(self) -> str:
        return self._project.id

    @property
    def key(self) -> str:
        return self._project.key

    @property
    def name(self) -> str:
        return self._project.name


class JiraClient:
    def __init__(self, server_url: str, token_tuple: Tuple[str, str]):
        self._client = jira.JIRA(
            server=server_url,
            basic_auth=token_tuple
        )

    def get_project(self, project_id: str) -> JiraProject | None:
        try:
            return JiraProject(self, self._client.project(project_id))
        except jira.JIRAError as e:
            if e.status_code == 404:
                return None

            raise e

    @property
    def base_url(self) -> str:
        return self._client.server_info()["baseUrl"]
