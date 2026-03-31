from __future__ import annotations

import logging
from typing import Any
from uuid import UUID
from src.server.server import mcp, resource_service
from src.core.config import get_settings
from src.schemas.tools import LOCAL_CLI_TRACK, STABLE_CARTESI_CLI, ALPHA_CARTESI_VERSION_PREFIX, STABLE_CREATE_TEMPLATES, ALPHA_CREATE_TEMPLATES, STABLE_OPTIONAL_RUN_SERVICES, ALPHA_OPTIONAL_RUN_SERVICES
from src.services.local_interaction_helpers import _command, _version_guidance, _alpha_warning, _alpha_v2_warning, _local_execution_steps, _local_execution_steps_for_binary, _cartesi_app_logic_next_steps, get_default_local_privatekeys, normalize_input_payload_to_hex

logger = logging.getLogger(__name__)
settings = get_settings()



# -----------------
# MCP tools
# -----------------


@mcp.tool(
    name="search_knowledge_resources",
    description="Search curated Cartesi knowledge resources by text query, source, tag, or kind and return matching resource cards.",
)
async def search_resources(
    query: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    kind: str | None = None,
    limit: int = 10,
) -> dict:
    """Searches curated Cartesi resources and returns lightweight result cards with MCP URIs and external links, but not full page body text."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        result = await svc.search_resources(query=query, tag=tag, source=source, kind=kind, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(result.cards)} matching resources.",
            "data": result.model_dump(mode="json"),
            "warnings": [
                "This server currently returns metadata and links only, not fetched page contents.",
            ],
            "next_steps": [
                "Use the returned resource URI to fetch a full resource document.",
                "Use search_doc_routes for route-level documentation lookup.",
                "If you need the source page contents, fetch the returned canonical_url separately.",
            ],
        }


@mcp.tool(
    name="get_resource_detail",
    description="Get normalized metadata for a single resource by resource ID, with optional documentation routes.",
)
async def get_resource_details(resource_id: str, include_routes: bool = True) -> dict:
    """Fetches a fully normalized resource document by resource ID, including external links and related routes but not fetched page body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(UUID(resource_id), include_routes=include_routes)
        return {
            "status": "success",
            "summary": f"Loaded resource '{detail.title}'.",
            "data": detail.model_dump(mode="json"),
            "warnings": [
                "This payload does not include the full contents of the external page.",
            ],
            "next_steps": [
                "Use linked URIs to fetch related repository or documentation views.",
                "Fetch data.canonical_url separately when you need the actual page contents.",
            ],
        }


@mcp.tool(
    name="list_resource_doc_routes",
    description="List documentation routes for one documentation resource, optionally filtered by section.",
)
async def list_doc_routes(resource_id: str, section: str | None = None, limit: int = 25) -> dict:
    """Lists documentation routes for a documentation resource, optionally filtered by section; results include route links but not fetched route body text."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        payload = await svc.list_doc_routes(UUID(resource_id), section=section, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(payload.routes)} documentation routes for '{payload.resource_title}'.",
            "data": payload.model_dump(mode="json"),
            "warnings": [
                "Route entries expose metadata and URLs, not the fetched contents of those URLs.",
            ],
            "next_steps": [
                "Use the route URI to load one route with its parent resource context.",
                "Fetch the selected route URL separately when you need the actual doc page contents.",
            ],
        }


@mcp.tool(
    name="search_documentation_routes",
    description="Search documentation routes across resources using query text with optional section, source, and tag filters.",
)
async def search_doc_routes(
    query: str,
    section: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    limit: int = 10,
) -> dict:
    """Searches indexed documentation routes across all tracked documentation resources and returns route metadata plus links, not fetched route body text."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        rows = await svc.search_doc_routes(query=query, section=section, source=source, tag=tag, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(rows)} matching documentation routes.",
            "data": {"results": rows},
            "warnings": [
                "Search results do not include full documentation page contents.",
            ],
            "next_steps": [
                "Use the route URI to inspect a single route in more detail.",
                "Fetch the selected route URL separately when you need the actual doc page contents.",
            ],
        }


@mcp.tool(
    name="list_resources_for_tag",
    description="List resources associated with a specific tag title.",
)
async def list_resources_by_tag(tag_title: str, limit: int = 10) -> dict:
    """Lists resources associated with a specific tag."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        result = await svc.list_resources_by_tag(tag_title=tag_title, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(result.cards)} resources tagged '{tag_title}'.",
            "data": result.model_dump(mode="json"),
            "warnings": [],
            "next_steps": [],
        }


@mcp.tool(
    name="list_resources_for_source",
    description="List resources associated with a specific source title.",
)
async def list_resources_by_source(source_title: str, limit: int = 10) -> dict:
    """Lists resources associated with a specific source, such as core contributors or community."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        result = await svc.list_resources_by_source(source_title=source_title, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(result.cards)} resources for source '{source_title}'.",
            "data": result.model_dump(mode="json"),
            "warnings": [],
            "next_steps": [],
        }


@mcp.tool(
    name="get_repository_sync_status",
    description="Get synchronization freshness and metadata for a repository-backed resource.",
)
async def get_repository_status(resource_id: str) -> dict:
    """Returns sync freshness and metadata for one tracked repository resource."""
    async with resource_service() as svc:
        payload = await svc.get_repository_status(UUID(resource_id))
        return {
            "status": "success",
            "summary": f"Loaded repository status for '{payload.title}'.",
            "data": payload.model_dump(mode="json"),
            "warnings": [],
            "next_steps": [],
        }


@mcp.tool(
    name="build_debugging_context",
    description="Build issue-focused context by combining relevant resources and documentation routes for a debugging query.",
)
async def get_debugging_context(query: str, prefer_official_only: bool = False, limit: int = 8) -> dict:
    """Returns the best matching docs and resources for debugging a Cartesi issue or concept, with metadata and links for follow-up fetching."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        payload = await svc.get_debugging_context(query=query, prefer_official_only=prefer_official_only, limit=limit)
        return {
            "status": "success",
            "summary": "Generated debugging context from curated resources and documentation routes.",
            "data": payload,
            "warnings": [
                "The returned matches are curated pointers; fetch the linked external pages when you need full text.",
            ],
            "next_steps": [
                "Open the returned MCP URIs for full resource details.",
                "Narrow results with tags or source if you need more precision.",
                "Fetch the canonical_url or route url of the most relevant matches to inspect full contents.",
            ],
        }


@mcp.tool(
    name="get_knowledge_taxonomy",
    description="Return the canonical taxonomy of known tag titles and source titles in the knowledge base.",
)
async def get_taxonomy() -> dict:
    """Returns available source names and tag names known to the knowledge base."""
    async with resource_service() as svc:
        tags = await svc.get_tag_catalog()
        sources = await svc.get_source_catalog()
        return {
            "status": "success",
            "summary": "Loaded source and tag taxonomy.",
            "data": {"tags": tags, "sources": sources},
            "warnings": [],
            "next_steps": [],
        }
    

@mcp.tool(
    name="summarize_knowledge_base",
    description="Return high-level knowledge-base coverage, counts by type, and orientation guidance for follow-up retrieval.",
)
async def get_knowledge_base_summary() -> dict:
    """
    Returns a high-level overview of the knowledge base: counts by type,
    all tags, and all sources. Agents should call this first to orient
    themselves before searching or reading specific resources.
    """
    async with resource_service() as svc:
        summary = await svc.get_knowledge_base_summary()
        return {
            "status": "success",
            "summary": "Loaded knowledge base summary.",
            "data": {
                **summary,
                "how_to_use": {
                    "step_1": "Call get_knowledge_base_summary to understand what exists (you are here).",
                    "step_2": "Call search_resources with query/tag/source filters to find relevant items.",
                    "step_3": "Read cartesi://resources/{resource_id} for normalized metadata and related links for a specific resource.",
                    "step_4": "For documentation, use list_doc_routes or search_doc_routes to navigate sub-routes and identify the best route URL.",
                    "step_5": "Fetch canonical_url or route url separately when you need the actual page contents, since this server currently returns links rather than stored page bodies.",
                },
            },
            "warnings": [
                "This knowledge base currently provides metadata, route indexes, and external links rather than full fetched page contents.",
            ],
            "next_steps": [
                "Use search_resources to locate resources by query, tag, source, or kind.",
                "Fetch specific resource details with get_resource_details(resource_id).",
                "Fetch the returned external URLs separately when deeper content inspection is required.",
            ],
        }


@mcp.tool(
    name="prepare_cartesi_create_command",
    description="Generate step-by-step host-machine instructions for creating a Cartesi app with the user's own Cartesi CLI.",
)
async def prepare_cartesi_create_command(
    project_name: str,
    template: str,
    destination_root: str = ".",
    template_branch: str | None = None,
    cli_track: LOCAL_CLI_TRACK = "unknown",
) -> dict:
    warnings: list[str] = []
    stable_command: str | None = None
    alpha_command: str | None = None

    if template not in STABLE_CREATE_TEMPLATES:
        warnings.append(
            "The requested template is not part of the known stable v1.5.x template list; verify it locally with `cartesi create --help`."
        )
    else:
        command_parts = ["cartesi", "create", project_name, "--template", template]
        if template_branch:
            command_parts += ["--branch", template_branch]
        stable_command = _command(command_parts)

    alpha_branch = template_branch or "prerelease/sdk-12"
    if template not in ALPHA_CREATE_TEMPLATES:
        warnings.append(
            "The requested template is not part of the known Cartesi 2.0 alpha template list; verify it locally with `cartesi create --help`."
        )
    else:
        alpha_parts = ["cartesi", "create", project_name, "--template", template, "--branch", alpha_branch]
        alpha_command = _command(alpha_parts)

    warnings.extend(_alpha_warning("create"))
    warnings.extend(_alpha_v2_warning("create"))

    return {
        "status": "success",
        "summary": f"Prepared host-side create instructions for project `{project_name}`.",
        "data": {
            "execution_location": "Run these commands on the user's machine, not on this MCP server.",
            "version_guidance": _version_guidance(cli_track),
            "requested_input": {
                "project_name": project_name,
                "template": template,
                "destination_root": destination_root,
                "template_branch": template_branch,
            },
            "stable_v1_5": {
                "working_directory": destination_root,
                "command": stable_command,
                "expected_templates": list(STABLE_CREATE_TEMPLATES),
            },
            "alpha_v2_0": {
                "binary": "cartesi",
                "working_directory": destination_root,
                "command": alpha_command,
                "default_branch": "prerelease/sdk-12",
                "expected_templates": list(ALPHA_CREATE_TEMPLATES),
            },
            "local_preflight": [
                "cartesi --version",
                "cartesi create --help",
            ],
        },
        "warnings": warnings,
        "next_steps": [
            *_local_execution_steps("create", stable_command or "cartesi create --help", destination_root),
            *_local_execution_steps_for_binary("create", alpha_command or "cartesi create --help", destination_root, "cartesi"),
            *_cartesi_app_logic_next_steps(destination_root),
        ],
    }


@mcp.tool(
    name="get_cartesi_app_logic_guidance",
    description="Explain what an agent should check when implementing Cartesi application logic, including address-book usage and relevant documentation/tutorial topics.",
)
async def get_cartesi_app_logic_guidance(project_path: str = ".") -> dict:
    return {
        "status": "success",
        "summary": "Prepared Cartesi application logic implementation guidance.",
        "data": {
            "execution_location": "Run any CLI commands on the user's machine, not on this MCP server.",
            "project_path": project_path,
            "required_local_command": "cartesi address-book",
            "why_address_book_matters": [
                "Use it to retrieve the local contract addresses and names needed for deposits and token interactions.",
                "Typical references include InputBox, ERC20Portal, ERC721Portal, and other portal-related contracts exposed by the local environment.",
            ],
            "implementation_topics": [
                "deposits",
                "ERC20 interactions",
                "ERC721 interactions",
                "ERC20Portal usage",
                "ERC721Portal usage",
                "Sending inputs and assets"
                "InputBox usage",
                "vouchers",
                "notices",
                "reports",
                "portal addresses",
            ],
            "recommended_doc_queries": [
                "InputBox",
                "ERC20 deposits",
                "ERC721 deposits",
                "vouchers",
                "notices",
                "reports",
                "portals",
                "Cartesi tutorials",
                "tutorials",
                "Cartesi documentation",
                "documentation",
                "docs",
                "Cartesi guide",
                "app demo"
                "demo"
                "integration"
                "integration guide"
                "tutorial"
            ],
        },
        "warnings": [
            "The MCP server can explain the workflow, but `cartesi address-book` must be run on the user's machine.",
        ],
        "next_steps": _cartesi_app_logic_next_steps(project_path),
    }


@mcp.tool(
    name="prepare_cartesi_build_command",
    description="Generate step-by-step host-machine instructions for building a Cartesi app with the user's own Cartesi CLI.",
)
async def prepare_cartesi_build_command(
    project_path: str,
    from_image: str | None = None,
    target: str | None = None,
    cli_track: LOCAL_CLI_TRACK = "unknown",
) -> dict:
    command_parts = ["cartesi", "build"]
    if from_image:
        command_parts += ["--from-image", from_image]
    if target:
        command_parts += ["--target", target]
    stable_command = _command(command_parts)
    alpha_command = _command(["cartesi", "build"])

    return {
        "status": "success",
        "summary": f"Prepared host-side build instructions for `{project_path}`.",
        "data": {
            "execution_location": "Run these commands on the user's machine, not on this MCP server.",
            "version_guidance": _version_guidance(cli_track),
            "requested_input": {
                "project_path": project_path,
                "from_image": from_image,
                "target": target,
            },
            "stable_v1_5": {
                "working_directory": project_path,
                "command": stable_command,
            },
            "alpha_v2_0": {
                "binary": "cartesi",
                "working_directory": project_path,
                "command": alpha_command,
                "known_flags": [
                    "--config <config>",
                    "--drives-only",
                    "--verbose",
                ],
            },
            "local_preflight": [
                "cartesi --version",
                "cartesi build --help",
            ],
        },
        "warnings": [
            *_alpha_warning("build"),
            *_alpha_v2_warning("build"),
            "Cartesi 2.0 alpha build uses a different flow from stable: bundled command definitions show `--config`, `--drives-only`, and `--verbose`, not stable's `--from-image` or `--target` flags.",
            *(
                ["The provided `from_image` input maps to stable v1.5.x only; there is no known direct `cartesi build` equivalent from the inspected alpha bundle."]
                if from_image
                else []
            ),
            *(
                ["The provided `target` input maps to stable v1.5.x only; Cartesi 2.0 alpha exposes `--config` instead in the inspected bundle, so the agent should re-check `cartesi build --help` locally before translating this input."]
                if target
                else []
            ),
        ],
        "next_steps": [
            *_local_execution_steps("build", stable_command, project_path),
            *_local_execution_steps_for_binary("build", alpha_command, project_path, "cartesi"),
        ],
    }


@mcp.tool(
    name="prepare_cartesi_run_command",
    description="Generate step-by-step host-machine instructions for running a Cartesi app with the user's own Cartesi CLI.",
)
async def prepare_cartesi_run_command(
    project_path: str,
    listen_port: int = 8080,
    block_time: int = 5,
    epoch_length: int = 720,
    services: list[str] | None = None,
    cpus: int | None = None,
    memory_mb: int | None = None,
    verbose: bool = False,
    no_backend: bool = False,
    cli_track: LOCAL_CLI_TRACK = "unknown",
) -> dict:
    requested_services = set(services or [])
    unsupported_service_toggles = sorted(requested_services - STABLE_OPTIONAL_RUN_SERVICES)
    unsupported_alpha_services = sorted(requested_services - ALPHA_OPTIONAL_RUN_SERVICES)

    command_parts = [
        "cartesi",
        "run",
        "--listen-port",
        str(listen_port),
        "--block-time",
        str(block_time),
        "--epoch-length",
        str(epoch_length),
    ]
    if cpus is not None:
        command_parts += ["--cpus", str(cpus)]
    if memory_mb is not None:
        command_parts += ["--memory", str(memory_mb)]
    if verbose:
        command_parts.append("--verbose")
    if no_backend:
        command_parts.append("--no-backend")
    for service in sorted(STABLE_OPTIONAL_RUN_SERVICES - requested_services):
        command_parts.append(f"--disable-{service}")

    warnings = _alpha_warning("run")
    warnings.extend(_alpha_v2_warning("run"))
    if unsupported_service_toggles:
        warnings.append(
            "Stable v1.5.x only exposes toggles for these optional services: bundler, explorer, paymaster. "
            f"These requested services cannot be mapped directly: {', '.join(unsupported_service_toggles)}."
        )

    alpha_parts = [
        "cartesi",
        "run",
        "--port",
        str(listen_port),
        "--block-time",
        str(block_time),
        "--epoch-length",
        str(epoch_length),
        "--default-block",
        "latest",
    ]
    if cpus is not None:
        alpha_parts += ["--cpus", str(cpus)]
    if memory_mb is not None:
        alpha_parts += ["--memory", str(memory_mb)]
    if verbose:
        alpha_parts.append("--verbose")
    if requested_services:
        alpha_parts += ["--services", ",".join(sorted(requested_services))]
    alpha_command = _command(alpha_parts)
    if unsupported_alpha_services:
        warnings.append(
            "Cartesi 2.0 alpha bundled command definitions only mention these service names: bundler, espresso, explorer, graphql, paymaster. "
            f"These requested services cannot be mapped directly: {', '.join(unsupported_alpha_services)}."
        )
    if no_backend:
        warnings.append("`no_backend` is known for stable v1.5.x, but no equivalent flag was found in the inspected Cartesi 2.0 alpha run bundle.")

    stable_command = _command(command_parts)

    return {
        "status": "success",
        "summary": f"Prepared host-side run instructions for `{project_path}`.",
        "data": {
            "execution_location": "Run these commands on the user's machine, not on this MCP server.",
            "version_guidance": _version_guidance(cli_track),
            "requested_input": {
                "project_path": project_path,
                "listen_port": listen_port,
                "block_time": block_time,
                "epoch_length": epoch_length,
                "services": sorted(requested_services),
                "cpus": cpus,
                "memory_mb": memory_mb,
                "verbose": verbose,
                "no_backend": no_backend,
            },
            "stable_v1_5": {
                "working_directory": project_path,
                "command": stable_command,
                "optional_service_toggles": sorted(STABLE_OPTIONAL_RUN_SERVICES),
            },
            "alpha_v2_0": {
                "binary": "cartesi",
                "working_directory": project_path,
                "command": alpha_command,
                "known_flags": [
                    "--prt",
                    "--block-time <number>",
                    "--cpus <number>",
                    "--default-block <string>",
                    "--dry-run",
                    "--fork-url <url>",
                    "--fork-block-number <number>",
                    "--memory <number>",
                    "--epoch-length <number>",
                    "--port <number>",
                    "--project-name <string>",
                    "--services <string>",
                    "--verbose",
                ],
                "optional_services": sorted(ALPHA_OPTIONAL_RUN_SERVICES),
            },
            "local_preflight": [
                "cartesi --version",
                "cartesi run --help",
            ],
        },
        "warnings": warnings,
        "next_steps": [
            *_local_execution_steps("run", stable_command, project_path),
            *_local_execution_steps_for_binary("run", alpha_command, project_path, "cartesi"),
        ],
    }


@mcp.tool(
    name="send_input_to_application",
    description="Generate host-machine instructions for sending an input to a running Cartesi application through the InputBox using cast.",
)
async def send_input_to_application(
    application_address: str | None,
    input_payload: str | dict[str, Any] | list[Any],
    rpc_url: str | None = None,
    cli_track: LOCAL_CLI_TRACK = "unknown",
    project_path: str = ".",
) -> dict:
    input_hex = normalize_input_payload_to_hex(input_payload)
    private_keys = get_default_local_privatekeys()
    selected_private_key = private_keys[0]

    cast_command = _command(
        [
            "cast",
            "send",
            "$input_box_address",
            "addInput(address,bytes)",
            application_address or "$application_address",
            input_hex,
            "--private-key",
            selected_private_key,
            "--rpc-url",
            rpc_url or "$rpc_url",
        ]
    )

    warnings: list[str] = []
    if application_address is None:
        warnings.append("The application address is required before sending input. Retrieve it from the running application context before executing the cast command.")
    if rpc_url is None:
        warnings.append("The RPC URL is required before sending input. For stable v1.5.x the common default is `http://127.0.0.1:8545`; for versions that start with `2.0.0`, the CLI run output may expose an application-specific RPC URL.")

    return {
        "status": "success",
        "summary": "Prepared host-side instructions for sending an input to a Cartesi application.",
        "data": {
            "execution_location": "Run these commands on the user's machine, not on this MCP server.",
            "version_guidance": _version_guidance(cli_track),
            "requirements": {
                "cast_install_check": [
                    "command -v cast",
                    "cast --version",
                ],
                "required_values": [
                    "application_address",
                    "rpc_url",
                    "input_box_address",
                    "hex_input_payload",
                ],
            },
            "rpc_url_guidance": {
                "stable_v1_5": "Usually `http://127.0.0.1:8545` for local dev flows.",
                "version_starts_with_2_0_0": "Read the RPC URL from the output of `cartesi run` for the specific running application.",
            },
            "address_book_guidance": {
                "command": "cartesi address-book",
                "purpose": "Use this to find the InputBox and related local contract addresses before sending inputs.",
                "target_contract": "InputBox",
            },
            "input_payload": {
                "original": input_payload,
                "normalized_hex": input_hex,
                "normalization_rule": "If the payload already starts with 0x and is valid hex, it is used as-is. Otherwise it is UTF-8 or JSON encoded and then converted to 0x-prefixed hex.",
            },
            "private_keys": {
                "default_signer_for_single_interaction": selected_private_key,
                "all_default_local_private_keys": private_keys,
                "usage_guidance": "Use the first private key for a single interaction by default. If multiple transactions must be signed by different individuals, assign different keys from this list to different actors.",
            },
            "stable_cast_command_template": cast_command,
        },
        "warnings": warnings,
        "next_steps": [
            "Run `command -v cast` and `cast --version` on the user's machine to confirm cast is installed.",
            "Obtain the application address for the running Cartesi app.",
            "Determine the RPC URL for the running app. For stable v1.5.x, `http://127.0.0.1:8545` is commonly used. For versions that start with `2.0.0`, inspect the `cartesi run` output for the app-specific RPC URL.",
            "Run `cartesi address-book` on the user's machine and capture the InputBox address.",
            f"Change into the relevant project directory on the user's machine if needed: `{project_path}`.",
            f"Run this command on the user's machine after replacing the shell variables with real values: `{cast_command}`",
            "If you need multiple distinct users to send transactions, reuse the same command with different private keys from the returned list.",
        ],
    }


