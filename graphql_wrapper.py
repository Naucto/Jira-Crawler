from graphql_client import Client
from graphql_client.custom_queries import Query
from graphql_client.custom_fields import (
        UserFields,
        RepositoryFields,
        RepositoryOwnerInterface,
        ProjectV2ConnectionFields, 
        ProjectV2Fields,
        IssueTypeConnectionFields,
        IssueTypeFields,
        CreateIssuePayloadFields,
        IssueConnectionFields,
        IssueEdgeFields,
        IssueFields
)
from graphql_client.custom_mutations import Mutation
from graphql_client.input_types import CreateIssueInput

from typing import Dict, Any


class QlUser:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._login = raw_body["login"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def login(self) -> str:
        return self._login


class QlProject:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._title = raw_body["title"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title


class QlIssueType:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._name = raw_body["name"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._name


class QlIssue:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._title = raw_body["title"]
        self._closed = raw_body["closed"]
        self._body_text = raw_body["bodyText"]
        self._created_at = raw_body["createdAt"]
        self._updated_at = raw_body["updatedAt"]
        self._closed_at = raw_body["closedAt"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def body_text(self) -> str:
        return self._body_text

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def closed_at(self) -> str | None:
        return self._closed_at


class Repository:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._ownerId = raw_body["owner"]["id"]
        self._ownerLogin = raw_body["owner"]["login"]

        self._name = raw_body["name"]

    async def get_projects(self, max_projects: int = 100) -> list[QlProject]:
        query = Query.repository(
            owner=self._ownerLogin,
            name=self._name
        ).fields(
            RepositoryFields.projects_v_2(
                first=max_projects
            ).fields(
                ProjectV2ConnectionFields.nodes().fields(
                    ProjectV2Fields.id,
                    ProjectV2Fields.title
                )
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")

        return list(
            map(lambda node: QlProject(self._client, node),
                response["repository"]["projectsV2"]["nodes"])
        )

    async def get_issue_types(self, max_types: int = 100) -> list[QlIssueType]:
        query = Query.repository(
            owner=self._ownerLogin,
            name=self._name
        ).fields(
            RepositoryFields.issue_types(
                first=max_types
            ).fields(
                IssueTypeConnectionFields.nodes().fields(
                    IssueTypeFields.id,
                    IssueTypeFields.name
                )
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")

        return list(
            map(lambda node: QlIssueType(self._client, node),
                response["repository"]["issueTypes"]["nodes"])
        )

    async def get_issues(self) -> list[QlIssue]:
        transformed_issues = []
        cursor = None

        while True:
            query = Query.repository(
                owner=self._ownerLogin,
                name=self._name
            ).fields(
                RepositoryFields.issues(
                    first=100,
                    after=cursor
                ).fields(
                    IssueConnectionFields.edges().fields(
                        IssueEdgeFields.cursor
                    ),
                    IssueConnectionFields.nodes().fields(
                        IssueFields.id,
                        IssueFields.title,
                        IssueFields.closed,
                        IssueFields.body_text,
                        IssueFields.created_at,
                        IssueFields.updated_at,
                        IssueFields.closed_at
                    )
                )
            )

            response = await self._client.raw.query(query, operation_name="repository")

            transformed_issues += list(
                map(lambda node: QlIssue(self._client, node),
                    response["repository"]["issues"]["nodes"])
            )

            # FIXME: 100 is a hard limit, hardcoded here but fine for our use case

            if len(transformed_issues) < 100:
                break

            cursor = response["repository"]["issues"]["edges"][-1]["cursor"]

        return transformed_issues

    async def create_issue(self, issue_type: QlIssueType, title: str, body: str) -> QlIssue:
        mutation = Mutation.create_issue(
            CreateIssueInput(
                repositoryId=self._id,
                title=title,
                body=body,
                issueTypeId=issue_type.id
            )
        ).fields(
            CreateIssuePayloadFields.issue().fields(
                IssueFields.id,
                IssueFields.title,
                IssueFields.closed,
                IssueFields.body_text,
                IssueFields.created_at,
                IssueFields.updated_at,
                IssueFields.closed_at
            )
        )

        response = await self._client.raw.mutation(mutation, operation_name="createIssue")

        return QlIssue(self._client, response["createIssue"]["issue"])

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def ownerId(self) -> str:
        return self._ownerId

    @property
    def ownerLogin(self) -> str:
        return self._ownerLogin


class GitHubGraphQlClient:
    def __init__(self, github_token: str):
        self._client = Client(
            url="https://api.github.com/graphql",
            headers={"authorization": f"Bearer {github_token}"}
        )

    async def get_repository(self, owner: str, name: str) -> Repository:
        query = Query.repository(
            owner=owner,
            name=name
        ).fields(
            RepositoryFields.id,
            RepositoryFields.name,
            RepositoryFields.owner().fields(
                RepositoryOwnerInterface.id,
                RepositoryOwnerInterface.login
            )
        )

        response = await self._client.query(query, operation_name="repository")

        return Repository(self, response["repository"])

    async def get_viewer(self) -> QlUser:
        query = Query.viewer().fields(
            UserFields.id,
            UserFields.login
        )

        response = await self._client.query(query, operation_name="viewer")

        return QlUser(self, response["viewer"])

    @property
    def raw(self) -> Client:
        return self._client
