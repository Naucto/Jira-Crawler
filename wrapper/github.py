from .graphql_client import Client
from .graphql_client.custom_queries import Query
from .graphql_client.custom_fields import (
        UserFields,
        UserConnectionFields,
        RepositoryFields,
        RepositoryOwnerInterface,
        ProjectV2ConnectionFields, 
        ProjectV2Fields,
        IssueTypeConnectionFields,
        IssueTypeFields,
        IssueConnectionFields,
        IssueEdgeFields,
        IssueFields,
        CreateIssuePayloadFields,
        DeleteIssuePayloadFields,
        UpdateIssuePayloadFields,
        RemoveAssigneesFromAssignablePayloadFields,
        AddAssigneesToAssignablePayloadFields
)
from .graphql_client.custom_mutations import Mutation
from .graphql_client.input_types import (
        IssueState,
        CreateIssueInput,
        DeleteIssueInput,
        UpdateIssueInput,
        RemoveAssigneesFromAssignableInput,
        AddAssigneesToAssignableInput
)

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

        # If created, assigned users will be empty
        self._assigned_users = list(
            map(
                lambda node: QlUser(self._client, node),
                raw_body.get("assignees", {}).get("nodes", [])
            )
        )

        self._id = raw_body["id"]
        self._title = raw_body["title"]
        self._closed = raw_body["closed"]
        self._body_text = raw_body["bodyText"]
        self._created_at = raw_body["createdAt"]
        self._updated_at = raw_body["updatedAt"]
        self._closed_at = raw_body["closedAt"]

        self._prev_assigned_users = list(self._assigned_users)
        self._prev_closed = self._closed

    async def delete(self) -> None:
        mutation = Mutation.delete_issue(
            DeleteIssueInput(issueId=self._id)
        ).fields(
            DeleteIssuePayloadFields.client_mutation_id
        )

        await self._client.raw.mutation(mutation, operation_name="deleteIssue")

    async def update(self) -> None:
        update_input = {
            "id": self._id,
            "title": self._title,
            "body": self._body_text,
        }

        if self._closed != self._prev_closed:
            update_input["state"] = IssueState.CLOSED if self._closed else IssueState.OPEN

        mutation = Mutation.update_issue(
            UpdateIssueInput(**update_input)
        ).fields(
            UpdateIssuePayloadFields.client_mutation_id
        )

        await self._client.raw.mutation(mutation, operation_name="updateIssue")

        # Get which users were removed
        removed_users = list(
            map(lambda user: user.id, filter(
                lambda user: user not in self._assigned_users,
                self._prev_assigned_users
            ))
        )

        if removed_users:
            mutation = Mutation.remove_assignees_from_assignable(
                RemoveAssigneesFromAssignableInput(
                    assignableId=self._id,
                    assigneeIds=removed_users
                )
            ).fields(
                RemoveAssigneesFromAssignablePayloadFields.client_mutation_id
            )

            await self._client.raw.mutation(mutation, operation_name="removeAssigneesFromAssignable")

        # Get which users were added
        added_users = list(
            map(lambda user: user.id, filter(
                lambda user: user not in self._prev_assigned_users,
                self._assigned_users
            ))
        )

        if added_users:
            mutation = Mutation.add_assignees_to_assignable(
                AddAssigneesToAssignableInput(
                    assignableId=self._id,
                    assigneeIds=list(map(lambda user: user.id, self._assigned_users))
                )
            ).fields(
                AddAssigneesToAssignablePayloadFields.client_mutation_id
            )

            await self._client.raw.mutation(mutation, operation_name="addAssigneesToAssignable")

    @property
    def id(self) -> str:
        return self._id

    @property
    def assigned_users(self) -> list[QlUser]:
        return self._assigned_users

    @assigned_users.setter
    def assigned_users(self, new_assigned_users: list[QlUser]) -> None:
        self._assigned_users = new_assigned_users

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, new_title: str) -> None:
        self._title = new_title

    @property
    def closed(self) -> bool:
        return self._closed

    @closed.setter
    def closed(self, new_closed: bool) -> None:
        self._closed = new_closed

    @property
    def body_text(self) -> str:
        return self._body_text

    @body_text.setter
    def body_text(self, new_body_text: str) -> None:
        self._body_text = new_body_text

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
            RepositoryFields.projects_v2(
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
                    IssueConnectionFields.nodes().fields(
                        IssueFields.assignees(first=100).fields(
                            UserConnectionFields.nodes().fields(
                                UserFields.id,
                                UserFields.login
                            )
                        ),
                        IssueFields.id,
                        IssueFields.title,
                        IssueFields.closed,
                        IssueFields.body_text,
                        IssueFields.created_at,
                        IssueFields.updated_at,
                        IssueFields.closed_at
                    ),
                    IssueConnectionFields.edges().fields(
                        IssueEdgeFields.cursor
                    )
                )
            )

            response = await self._client.raw.query(query, operation_name="repository")

            transformed_issues += list(
                map(lambda node: QlIssue(self._client, node),
                    response["repository"]["issues"]["nodes"])
            )

            # FIXME: 100 is a hard limit, hardcoded here but fine for our use case

            if len(transformed_issues) < 100 or not response["repository"]["issues"]["edges"]:
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

    async def get_user(self, username_id: str) -> QlUser:
        query = Query.user(login=username_id).fields(
            UserFields.id,
            UserFields.login
        )

        response = await self._client.query(query, operation_name="user")

        return QlUser(self, response["user"])

    @property
    def raw(self) -> Client:
        return self._client
