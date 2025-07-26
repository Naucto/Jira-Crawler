import jira
import jira.resources

from enum import Enum
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


class JiraIssueStatus(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    TO_REVIEW = "To Review" # This one is specific to our workflow, not standard in Jira
    DONE = "Done"

    @staticmethod
    def from_jira_status(status: jira.resources.Status) -> "JiraIssueStatus":
        match status.name.lower():
            case "to-do":
                return JiraIssueStatus.TODO
            case "in progress":
                return JiraIssueStatus.IN_PROGRESS
            case "to review":
                return JiraIssueStatus.TO_REVIEW
            case "done":
                return JiraIssueStatus.DONE
            case _:
                raise ValueError(f"Unknown Jira status: {status.name}")


class JiraIssue:
    def __init__(self, jira: "JiraClient", issue_id: str):
        self._jira = jira
        self._id = issue_id

        self._issue = self._jira.client.issue(issue_id)

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
    def assignee(self) -> JiraUser | None:
        if self._issue.fields.assignee is None:
            return None

        return JiraUser(
            self._jira.client.user(id=self._issue.fields.assignee.accountId)
        )

    @property
    def status(self) -> JiraIssueStatus:
        return JiraIssueStatus.from_jira_status(self._issue.fields.status)

    @property
    def issue(self) -> jira.Issue:
        return self._issue


class JiraEpic(JiraIssue):
    def __init__(self, jira: "JiraClient", epic_id: str):
        super().__init__(jira, epic_id)

    @property
    def tasks(self) -> list[JiraIssue]:
        return list(map(lambda issue_id: JiraIssue(self._jira, issue_id),
            self._jira.client.search_issues(
                f'type=Task AND parent={self.id} ORDER BY created ASC',
                maxResults=False
            )
        ))


class JiraProject:
    def __init__(self, client: "JiraClient", project: jira.Project):
        self._client = client
        self._project = project

    def get_issues(self) -> list[JiraIssue]:
        return list(map(lambda issue_id: JiraIssue(self._client, issue_id),
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

        done_status = None
        statuses = self._client.statuses()

        for status in statuses:
            if status.name.lower() == "done":
                done_status = status
                break

        if done_status is None:
            raise ValueError(
                "No 'Done' status found in the Jira instance, please check your " +
                "Jira configuration to have its language set to English."
            )

        self._done_status = done_status

    def get_project(self, project_id: str) -> JiraProject | None:
        try:
            return JiraProject(self, self._client.project(project_id))
        except jira.JIRAError as e:
            if e.status_code == 404:
                return None

            raise e

    @property
    def client(self) -> jira.JIRA:
        return self._client

    @property
    def base_url(self) -> str:
        return self._client.server_info()["baseUrl"]

    @property
    def done_status(self) -> jira.resources.Status:
        return self._done_status
