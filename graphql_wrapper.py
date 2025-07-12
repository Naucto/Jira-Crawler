from graphql_client import Client
from graphql_client.custom_queries import Query
from graphql_client.custom_fields import (
        RepositoryFields,
        RepositoryOwnerInterface,
        ProjectV2ConnectionFields, 
        ProjectV2Fields
)

from typing import Dict, Any


class Project:
    def __init__(self, client: Client, raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._title = raw_body["title"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title


class Repository:
    def __init__(self, client: Client, raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._name = raw_body["name"]
        self._owner = raw_body["owner"]["login"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def owner(self) -> str:
        return self._owner

    async def get_projects(self, max_projects: int = 100) -> list[Project]:
        query = Query.repository(
            owner=self._owner,
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

        response = await self._client.query(query, operation_name="repository")

        return list(
            map(lambda node: Project(self._client, node),
                response["repository"]["projectsV2"]["nodes"])
        )


class GithubGraphQlClient:
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
                RepositoryOwnerInterface.login
            )
        )

        response = await self._client.query(query, operation_name="repository")

        return Repository(self._client, response["repository"])
