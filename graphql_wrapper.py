from graphql_client import Client
from graphql_client.custom_queries import Query
from graphql_client.custom_fields import (
        UserFields,
        RepositoryFields,
        RepositoryOwnerInterface,
        ProjectV2ConnectionFields, 
        ProjectV2Fields,
        IssueTypeConnectionFields,
        IssueTypeFields
)
# from graphql_client.custom_mutations import Mutation
# from graphql_client.input_types import CreateProjectV2Input

from typing import Dict, Any


class User:
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


class Project:
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


class IssueType:
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


class Repository:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._ownerId = raw_body["owner"]["id"]
        self._ownerLogin = raw_body["owner"]["login"]

        self._name = raw_body["name"]

    async def get_projects(self, max_projects: int = 100) -> list[Project]:
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
            map(lambda node: Project(self._client, node),
                response["repository"]["projectsV2"]["nodes"])
        )

    async def get_issue_types(self, max_types: int = 100) -> list[IssueType]:
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
            map(lambda node: IssueType(self._client, node),
                response["repository"]["issueTypes"]["nodes"])
        )

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

    async def get_viewer(self) -> User:
        query = Query.viewer().fields(
            UserFields.id,
            UserFields.login
        )

        response = await self._client.query(query, operation_name="viewer")

        return User(self, response["viewer"])

    @property
    def raw(self) -> Client:
        return self._client
