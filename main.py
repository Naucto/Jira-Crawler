#!/usr/bin/env python3.13

from loguru import logger as L
import trio

from crawler import Crawler

import os


L.info("Hello, world from Naucto's Jira Crawler!")

env_set = {
    "CW_JIRA_TOKEN": "jira_token",
    "CW_JIRA_PROJECT_ID": "jira_project_id",
    "CW_GITHUB_TOKEN": "github_token",
    "CW_GITHUB_TARGET": "github_repository"
}

for env_var_name, global_var_name in env_set.items():
    env_var_value = os.getenv(env_var_name)

    if env_var_value is None:
        L.error(f"Environment variable {env_var_name} is not set.")
        exit(1)

    globals()[global_var_name] = env_var_value

try:
    crawler = Crawler(
        jira_token=jira_token, # type: ignore
        jira_project_id=jira_project_id, # type: ignore
        github_token=github_token, # type: ignore
        github_repository=github_repository # type: ignore
    )
except Exception as e:
    L.error(f"Error while instanciating crawler: {e}")
    exit(1)


trio.run(crawler.crawl)
