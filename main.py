#!/usr/bin/env python3.13

from loguru import logger as L
import trio

from crawler import Crawler
from hosting import WebhookListener

from common import BridgeMapping

from typing import Optional
import os


L.info("Hello, world from Naucto's Jira Crawler!")

env_set = {
    "CW_JIRA_SERVER_URL": "jira_server_url",
    "CW_JIRA_TOKEN": "jira_token",
    "CW_JIRA_PROJECT_ID": "jira_project_id",
    "CW_GITHUB_TOKEN": "github_token",
    "CW_GITHUB_TARGET": "github_repository",
    "CW_BRIDGE_MAPPING": "bridge_mapping_config_path"
}

for env_var_name, global_var_name in env_set.items():
    env_var_value = os.getenv(env_var_name)

    if env_var_value is None:
        L.error(f"Environment variable {env_var_name} is not set.")
        exit(1)

    globals()[global_var_name] = env_var_value

host = bool(os.getenv("CW_HOST", None))
host_cert = os.getenv("CW_HOST_CERT", None)

if host: # type: ignore
    L.info("Starting as a self-sustaining updater through a webhook endpoint.")

try:
    crawler = Crawler(
        jira_server_url=jira_server_url, # type: ignore
        jira_token=jira_token, # type: ignore
        jira_project_id=jira_project_id, # type: ignore
        github_token=github_token, # type: ignore
        github_repository=github_repository, # type: ignore
        bridge_mapping=BridgeMapping(bridge_mapping_config_path) # type: ignore
    )
except Exception as e:
    L.error(f"Error while instanciating crawler: {e}")
    exit(1)

if host: # type: ignore
    resolved_host_cert: Optional[tuple[str, str]] = None

    if host_cert:
        host_cert_base = os.path.join(host_cert, "fullchain.pem")
        host_cert_key  = os.path.join(host_cert, "privkey.pem")
        resolved_host_cert = (host_cert_base, host_cert_key)
    else:
        L.warning("No HTTPS certificate path provided. The service will not be secure.")

    listener = WebhookListener(crawler, host_cert=resolved_host_cert)
    listener.run()
else:
    trio.run(crawler.crawl)
