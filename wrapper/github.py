from .graphql_client import Client
from .graphql_client.custom_queries import Query
from .graphql_client.custom_fields import (
        UserFields,
        UserConnectionFields,
        RepositoryFields,
        RepositoryOwnerInterface,
        ProjectV2ConnectionFields, 
        ProjectV2Fields,
        ProjectV2SingleSelectFieldFields,
        ProjectV2SingleSelectFieldOptionFields,
        ProjectV2ItemFields,
        ProjectV2ItemConnectionFields,
        ProjectV2ItemEdgeFields,
        MilestoneConnectionFields,
        MilestoneFields,
        IssueTypeConnectionFields,
        IssueTypeFields,
        IssueConnectionFields,
        IssueEdgeFields,
        IssueFields,
        CreateIssuePayloadFields,
        DeleteIssuePayloadFields,
        UpdateIssuePayloadFields,
        RemoveAssigneesFromAssignablePayloadFields,
        AddAssigneesToAssignablePayloadFields,
        AddProjectV2ItemByIdPayloadFields,
        UpdateProjectV2ItemFieldValuePayloadFields
)
from .graphql_client.custom_mutations import Mutation
from .graphql_client.input_types import (
        IssueState,
        CreateIssueInput,
        DeleteIssueInput,
        UpdateIssueInput,
        RemoveAssigneesFromAssignableInput,
        AddAssigneesToAssignableInput,
        AddProjectV2ItemByIdInput,
        ProjectV2FieldValue,
        UpdateProjectV2ItemFieldValueInput
)

from enum import Enum
from typing import Dict, Any


class QlUser:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._login = raw_body["login"]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, QlUser):
            return False

        return self._id == other._id and self._login == other._login

    @property
    def id(self) -> str:
        return self._id

    @property
    def login(self) -> str:
        return self._login


class QlMilestone:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._title = raw_body["title"]
        self._description = raw_body["description"]

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description


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


class QlIssueStatus(Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

    @classmethod
    def from_string(cls, status: str) -> "QlIssueStatus":
        return cls[status.upper().replace(" ", "_")]


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
        self._milestone = QlMilestone(self._client, raw_body["milestone"]) \
            if ("milestone" in raw_body and raw_body["milestone"] is not None) else None

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
            "milestone_id": self._milestone.id if self._milestone else None
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
    def milestone(self) -> QlMilestone | None:
        return self._milestone

    @milestone.setter
    def milestone(self, new_milestone: QlMilestone | None) -> None:
        self._milestone = new_milestone

    @property
    def created_at(self) -> str:
        return self._created_at

    @property
    def updated_at(self) -> str:
        return self._updated_at

    @property
    def closed_at(self) -> str | None:
        return self._closed_at


class QlProject:
    def __init__(self,
                 client: "GitHubGraphQlClient",
                 repository: "QlRepository", raw_body: Dict[str, Any]):
        self._client = client
        self._repository = repository

        self._id = raw_body["id"]
        self._number = raw_body["number"]
        self._title = raw_body["title"]

        self._field_ids: Dict[str, str] = {}
        self._status_field_option_ids: Dict[QlIssueStatus, str] = {}
        self._issue_item_ids: Dict[str, str] = {}

    async def _fetch_field_id(self, field_name: str) -> str:
        if field_name in self._field_ids:
            return self._field_ids[field_name]

        query = Query.repository(
            owner=self._repository._owner_login,
            name=self._repository._name
        ).fields(
            RepositoryFields.project_v2(
                number=self._number
            ).fields(
                ProjectV2Fields.field(name=field_name).on(
                    "ProjectV2SingleSelectField",
                    ProjectV2SingleSelectFieldFields.id
                )
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")
        field_id = response["repository"]["projectV2"]["field"]["id"]

        self._field_ids[field_name] = field_id
        return field_id

    async def _fetch_status_field_option_id(self, status: QlIssueStatus) -> str:
        if status in self._status_field_option_ids:
            return self._status_field_option_ids[status]

        query = Query.repository(
            owner=self._repository._owner_login,
            name=self._repository._name
        ).fields(
            RepositoryFields.project_v2(
                number=self._number
            ).fields(
                ProjectV2Fields.field(name="Status").on(
                    "ProjectV2SingleSelectField",
                    ProjectV2SingleSelectFieldFields.options().fields(
                        ProjectV2SingleSelectFieldOptionFields.id,
                        ProjectV2SingleSelectFieldOptionFields.name
                    )
                )
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")

        self._status_field_option_ids.update({
            QlIssueStatus.from_string(option["name"]): option["id"]
            for option in response["repository"]["projectV2"]["field"]["options"]
        })

        if status not in self._status_field_option_ids:
            raise ValueError(f"Status {status} not found in project {self._title}")

        return self._status_field_option_ids[status]

    async def _fetch_issue_item_id(self, issue: QlIssue) -> str:
        if issue.id in self._issue_item_ids:
            return self._issue_item_ids[issue.id]

        cursor = None

        while True:
            query = Query.repository(
                owner=self._repository._owner_login,
                name=self._repository._name
            ).fields(
                RepositoryFields.project_v2(
                    number=self._number
                ).fields(
                    ProjectV2Fields.items(
                        first=100,
                        after=cursor
                    ).fields(
                        ProjectV2ItemConnectionFields.nodes().fields(
                            ProjectV2ItemFields.id,
                            ProjectV2ItemFields.type
                        ),
                        ProjectV2ItemConnectionFields.edges().fields(
                            ProjectV2ItemEdgeFields.cursor
                        )
                    )
                )
            )

            response = await self._client.raw.query(query, operation_name="repository")

            self._issue_item_ids.update({
                item["id"]: item["id"]
                for item in response["repository"]["projectV2"]["items"]["nodes"]
                if item["id"] not in self._issue_item_ids and item["type"] == "ISSUE"
            })

            # FIXME: 100 is a hard limit, hardcoded here but fine for our use case

            if len(self._issue_item_ids) >= 100 or not response["repository"]["projectV2"]["items"]["edges"]:
                break

            cursor = response["repository"]["projectV2"]["items"]["edges"][-1]["cursor"]

        if issue.id not in self._issue_item_ids:
            raise ValueError(f"Issue {issue.id} not found in project {self._title}")

        return self._issue_item_ids[issue.id]


    async def add_issue(self, issue: QlIssue) -> None:
        mutation = Mutation.add_project_v_2_item_by_id(
            AddProjectV2ItemByIdInput(
                projectId=self._id,
                contentId=issue.id
            )
        ).fields(
            AddProjectV2ItemByIdPayloadFields.client_mutation_id,
            AddProjectV2ItemByIdPayloadFields.item().fields(
                ProjectV2ItemFields.id
            )
        )

        response = await self._client.raw.mutation(mutation, operation_name="addProjectV2Item")
        issue_item_id = response["addProjectV2ItemById"]["item"]["id"]

        self._issue_item_ids[issue.id] = issue_item_id

    async def set_issue_status(self, issue: QlIssue, status: QlIssueStatus) -> None:
        status_field_id: str = await self._fetch_field_id("Status")

        mutation = Mutation.update_project_v_2_item_field_value(
            UpdateProjectV2ItemFieldValueInput(
                projectId=self._id,
                itemId=await self._fetch_issue_item_id(issue),
                fieldId=status_field_id,
                value=ProjectV2FieldValue(
                    single_select_option_id=await self._fetch_status_field_option_id(status) # type: ignore
                )
            )
        ).fields(
            UpdateProjectV2ItemFieldValuePayloadFields.client_mutation_id
        )

        await self._client.raw.mutation(mutation, operation_name="updateProjectV2ItemFieldValue")

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title


class QlRepository:
    def __init__(self, client: "GitHubGraphQlClient", raw_body: Dict[str, Any]):
        self._client = client

        self._id = raw_body["id"]
        self._owner_id = raw_body["owner"]["id"]
        self._owner_login = raw_body["owner"]["login"]

        self._name = raw_body["name"]

    async def get_projects(self, max_projects: int = 100) -> list[QlProject]:
        query = Query.repository(
            owner=self._owner_login,
            name=self._name
        ).fields(
            RepositoryFields.projects_v2(
                first=max_projects
            ).fields(
                ProjectV2ConnectionFields.nodes().fields(
                    ProjectV2Fields.id,
                    ProjectV2Fields.number,
                    ProjectV2Fields.title
                )
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")

        return list(
            map(lambda node: QlProject(self._client, self, node),
                response["repository"]["projectsV2"]["nodes"])
        )

    async def get_issue_types(self, max_types: int = 100) -> list[QlIssueType]:
        query = Query.repository(
            owner=self._owner_login,
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
                owner=self._owner_login,
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
                        IssueFields.closed_at,
                        IssueFields.milestone().fields(
                            MilestoneFields.id,
                            MilestoneFields.title,
                            MilestoneFields.description
                        )
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
                IssueFields.closed_at,
                IssueFields.milestone().fields(
                    MilestoneFields.id,
                    MilestoneFields.title,
                    MilestoneFields.description
                )
            )
        )

        response = await self._client.raw.mutation(mutation, operation_name="createIssue")

        return QlIssue(self._client, response["createIssue"]["issue"])

    async def get_milestones(self, max_milestones: int = 100) -> list[QlMilestone]:
        query = Query.repository(
            owner=self._owner_login,
            name=self._name
        ).fields(
            RepositoryFields.milestones(
                first=max_milestones
            ).fields(
                MilestoneConnectionFields.nodes().fields(
                    MilestoneFields.id,
                    MilestoneFields.title,
                    MilestoneFields.description
                )
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")

        return list(
            map(lambda node: QlMilestone(self._client, node),
                response["repository"]["milestones"]["nodes"])
        )

    async def get_milestone(self, milestone_id: int) -> QlMilestone | None:
        query = Query.repository(
            owner=self._owner_login,
            name=self._name
        ).fields(
            RepositoryFields.milestone(number=milestone_id).fields(
                MilestoneFields.id,
                MilestoneFields.title,
                MilestoneFields.description
            )
        )

        response = await self._client.raw.query(query, operation_name="repository")

        return QlMilestone(self._client, response["repository"]["milestone"]) \
            if response["repository"]["milestone"] else None

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def owner_id(self) -> str:
        return self._owner_id

    @property
    def owner_login(self) -> str:
        return self._owner_login


class GitHubGraphQlClient:
    def __init__(self, github_token: str):
        self._client = Client(
            url="https://api.github.com/graphql",
            headers={"authorization": f"Bearer {github_token}"}
        )

    async def get_repository(self, owner: str, name: str) -> "QlRepository":
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

        return QlRepository(self, response["repository"])

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
