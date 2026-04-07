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


def _resolve_depositor_signing_key(
    bank: list[str],
    depositor_private_key: str | None,
    depositor_wallet_index: int,
) -> str:
    """
    Private key used for depositor-signed steps (approve, deposit, etc.).
    If `depositor_private_key` is non-empty, it wins; otherwise use `bank[depositor_wallet_index]`.
    """
    if depositor_private_key is not None and str(depositor_private_key).strip():
        return str(depositor_private_key).strip()
    if depositor_wallet_index < 0 or depositor_wallet_index >= len(bank):
        raise ValueError(
            f"depositor_wallet_index must be in [0, {len(bank) - 1}] for this dev key bank; got {depositor_wallet_index}."
        )
    return bank[depositor_wallet_index]


def _depositor_balance_holder_ref(depositor_address: str | None) -> str:
    """Literal address for balance/read calls, or `$holder_address` to fill from `cast wallet address`."""
    if depositor_address is not None and str(depositor_address).strip():
        return str(depositor_address).strip()
    return "$holder_address"


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


@mcp.tool(
    name="prepare_erc20_deposit_instructions",
    description="Generate host-machine instructions for depositing ERC20 tokens into a Cartesi application via ERC20Portal using cast: balance check, optional funding transfer, approve, and depositERC20Tokens. Depositor wallet is configurable via depositor_wallet_index, depositor_private_key, and optional depositor_address for read calls.",
)
async def prepare_erc20_deposit_instructions(
    application_address: str | None,
    token_amount: str,
    execution_layer_data: str = "0x",
    token_contract_address: str | None = None,
    rpc_url: str | None = None,
    depositor_wallet_index: int = 0,
    depositor_private_key: str | None = None,
    depositor_address: str | None = None,
    cli_track: LOCAL_CLI_TRACK = "unknown",
    project_path: str = ".",
) -> dict:
    """
    Returns cast command templates and an ordered workflow for ERC20 deposits.
    Does not execute anything on the MCP host; the agent runs commands on the user's machine.
    """
    private_keys = get_default_local_privatekeys()
    selected_private_key = _resolve_depositor_signing_key(
        private_keys, depositor_private_key, depositor_wallet_index
    )
    balance_holder_ref = _depositor_balance_holder_ref(depositor_address)
    exec_hex = (
        normalize_input_payload_to_hex(execution_layer_data)
        if execution_layer_data and execution_layer_data.strip()
        else "0x"
    )

    token_ref = token_contract_address or "$test_token_contract_address"
    app_ref = application_address or "$application_address"
    rpc_ref = rpc_url or "$rpc_url"

    balance_check_command = _command(
        [
            "cast",
            "call",
            token_ref,
            "balanceOf(address)(uint256)",
            balance_holder_ref,
            "--rpc-url",
            rpc_ref,
        ]
    )

    transfer_to_depositor_command = _command(
        [
            "cast",
            "send",
            token_ref,
            "transfer(address,uint256)",
            "$depositor_address",
            token_amount,
            "--rpc-url",
            rpc_ref,
            "--private-key",
            "$funding_wallet_private_key",
        ]
    )

    approve_command = _command(
        [
            "cast",
            "send",
            token_ref,
            "approve(address,uint256)",
            "$erc20_portal_address",
            token_amount,
            "--rpc-url",
            rpc_ref,
            "--private-key",
            selected_private_key,
        ]
    )

    deposit_command = _command(
        [
            "cast",
            "send",
            "$erc20_portal_address",
            "depositERC20Tokens(address,address,uint256,bytes)",
            token_ref,
            app_ref,
            token_amount,
            exec_hex,
            "--rpc-url",
            rpc_ref,
            "--private-key",
            selected_private_key,
        ]
    )

    holder_address_from_key_command = _command(
        [
            "cast",
            "wallet",
            "address",
            "--private-key",
            selected_private_key,
        ]
    )

    warnings: list[str] = []
    if application_address is None:
        warnings.append(
            "The application contract address is required before depositing. Obtain it from the running Cartesi application context."
        )
    if rpc_url is None:
        warnings.append(
            "The RPC URL is required. For stable v1.5.x the common default is `http://127.0.0.1:8545`; for versions that start with `2.0.0`, use the RPC URL from `cartesi run` output."
        )
    if token_contract_address is None:
        warnings.append(
            "No token address was provided: use the CLI-provided TestToken address from `cartesi address-book` (often minted to the first Anvil-style dev wallet) unless the user specifies another ERC20."
        )
    if depositor_address is not None and str(depositor_address).strip():
        warnings.append(
            "When `depositor_address` is set, it must match the address derived from the depositor signing key (`holder_address_from_key_command`); otherwise balance checks and transfers will disagree."
        )

    return {
        "status": "success",
        "summary": "Prepared host-side workflow for ERC20 deposits through ERC20Portal.",
        "data": {
            "execution_location": "Run these commands on the user's machine, not on this MCP server.",
            "version_guidance": _version_guidance(cli_track),
            "agent_workflow": [
                "Run `cartesi address-book` in the project directory and record ERC20Portal and TestToken (or the user-chosen token) contract addresses.",
                "Ensure the application logic knows which token address to expect for deposits (e.g. parse or compare against the deposited token) before relying on deposits in production.",
                "Depositor wallet: use `depositor_wallet_index` into the dev key bank, or pass `depositor_private_key` to simulate another signer (overrides the index). Optionally pass `depositor_address` so balance checks use that literal address; otherwise use `holder_address_from_key_command` and treat that address as `$depositor_address` for transfers.",
                "Check the depositor's token balance with `balance_check_command` (read-only `cast call`; no private key). The ABI selector is standard ERC-20 `balanceOf(address)`.",
                "If balance is zero or less than `token_amount`, ask the user for permission, then fund the depositor by sending tokens from any wallet that holds enough balance using `transfer_to_depositor_command` (replace `$funding_wallet_private_key` with that wallet's key). The Cartesi CLI TestToken is typically pre-minted to the first wallet in the local dev key bank; you can transfer from that wallet to the depositor.",
                "Have the depositor approve the ERC20Portal to pull tokens: run `approve_command` with the depositor's private key.",
                "Deposit into the application: run `deposit_command` with the same depositor private key. `execution_layer_data` is ABI-encoded `bytes` passed to the app (normalized hex below).",
            ],
            "default_token_guidance": {
                "when_no_token_specified": "Use the TestToken entry from `cartesi address-book`. It is deployed and minted for local dev; the default funding wallet is usually the first key in the local wallet bank (same list as `send_input_to_application`).",
                "transfer_source": "If another address must deposit, transfer TestToken from a funded wallet to `$depositor_address` using `transfer_to_depositor_command` after user consent.",
            },
            "requirements": {
                "cast_install_check": [
                    "command -v cast",
                    "cast --version",
                ],
                "required_values": [
                    "application_address",
                    "rpc_url",
                    "erc20_portal_address",
                    "token_contract_address (or TestToken from address-book)",
                    "token_amount (uint256, typically wei as a decimal string)",
                    "depositor private key for approve and deposit",
                    "funding wallet private key only if a transfer step is needed",
                ],
            },
            "rpc_url_guidance": {
                "stable_v1_5": "Usually `http://127.0.0.1:8545` for local dev flows.",
                "version_starts_with_2_0_0": "Read the RPC URL from the output of `cartesi run` for the specific running application.",
            },
            "address_book_guidance": {
                "command": "cartesi address-book",
                "purpose": "Resolve ERC20Portal and TestToken (or other listed token) addresses for the active Cartesi dev stack.",
                "target_contracts": ["ERC20Portal", "TestToken"],
            },
            "balance_check": {
                "description": "Read-only check that the depositor address holds at least `token_amount` before approve/deposit. Uses `depositor_address` when provided, otherwise the same address as `$holder_address` / `holder_address_from_key_command` output.",
                "command_template": balance_check_command,
                "notes": [
                    "This is `cast call`, not `cast send`: no transaction, no `--private-key`.",
                    "Return value is the uint256 balance in the token's smallest unit (same unit as `token_amount`).",
                ],
            },
            "execution_layer_data": {
                "original": execution_layer_data,
                "normalized_hex": exec_hex,
                "normalization_rule": "Same as input payload normalization: valid `0x` hex is kept; otherwise UTF-8 encoded to hex. Empty input becomes `0x`.",
            },
            "token_amount": {
                "value": token_amount,
                "note": "Must match the ERC-20 `uint256` amount (almost always whole token wei). Use the same numeric string for transfer (if used), approve, and deposit.",
            },
            "depositor_configuration": {
                "depositor_wallet_index": depositor_wallet_index,
                "depositor_private_key_source": "parameter" if (depositor_private_key and str(depositor_private_key).strip()) else "wallet_bank_index",
                "depositor_address_for_reads": depositor_address,
                "balance_check_uses_address": balance_holder_ref,
                "notes": [
                    "Change `depositor_wallet_index` (0-based into `all_default_local_private_keys`) to simulate deposits from different built-in dev wallets.",
                    "Pass `depositor_private_key` to use a key outside the bank; it overrides `depositor_wallet_index` for signing.",
                    "Pass `depositor_address` to pin balance/read calls to a specific hex address; if omitted, templates use `$holder_address` — set it from `holder_address_from_key_command` before running balance checks.",
                ],
            },
            "private_keys": {
                "depositor_signer": selected_private_key,
                "all_default_local_private_keys": private_keys,
                "usage_guidance": "Depositor signs approve and deposit. Use `depositor_wallet_index` or `depositor_private_key` to switch wallets. Use another key for `funding_wallet_private_key` when transferring from a wallet that already holds the token.",
            },
            "holder_address_from_key_command": holder_address_from_key_command,
            "cast_command_templates": {
                "transfer_to_depositor": transfer_to_depositor_command,
                "approve_erc20_portal": approve_command,
                "deposit_erc20_tokens": deposit_command,
            },
            "requested_input": {
                "application_address": application_address,
                "token_amount": token_amount,
                "token_contract_address": token_contract_address,
                "execution_layer_data": execution_layer_data,
                "rpc_url": rpc_url,
                "depositor_wallet_index": depositor_wallet_index,
                "depositor_private_key_provided": bool(depositor_private_key and str(depositor_private_key).strip()),
                "depositor_address": depositor_address,
                "project_path": project_path,
            },
        },
        "warnings": warnings,
        "next_steps": [
            "Run `command -v cast` and `cast --version` on the user's machine.",
            f"Change into the project directory if needed: `{project_path}`.",
            "Run `cartesi address-book` and copy ERC20Portal and token (TestToken or user-specified) addresses into the commands.",
            f"Obtain the depositor address if needed: `{holder_address_from_key_command}`, or use the configured `depositor_address` for read-only balance checks.",
            f"Check balance: `{balance_check_command}` — if insufficient, ask the user, then fund with `{transfer_to_depositor_command}`.",
            f"Approve: `{approve_command}`.",
            f"Deposit: `{deposit_command}`.",
        ],
    }


@mcp.tool(
    name="prepare_erc721_deposit_instructions",
    description="Generate host-machine instructions for depositing one ERC721 token into a Cartesi application via ERC721Portal: ownership/balance checks, optional safeMint (owner key only), transferFrom, setApprovalForAll, and depositERC721Token. Depositor wallet is configurable via depositor_wallet_index, depositor_private_key, and optional depositor_address for read calls.",
)
async def prepare_erc721_deposit_instructions(
    application_address: str | None,
    token_id: str,
    token_uri: str = "ipfs://cartesi-local-test-nft",
    base_layer_data: str = "0x",
    execution_layer_data: str = "0x",
    nft_contract_address: str | None = None,
    rpc_url: str | None = None,
    depositor_wallet_index: int = 0,
    depositor_private_key: str | None = None,
    depositor_address: str | None = None,
    cli_track: LOCAL_CLI_TRACK = "unknown",
    project_path: str = ".",
) -> dict:
    """
    Streamlined ERC721 deposit workflow for local dev (TestNFT from address-book when unset).
    """
    private_keys = get_default_local_privatekeys()
    owner_minter_private_key = private_keys[0]
    depositor_key = _resolve_depositor_signing_key(
        private_keys, depositor_private_key, depositor_wallet_index
    )
    balance_holder_ref = _depositor_balance_holder_ref(depositor_address)
    base_hex = (
        normalize_input_payload_to_hex(base_layer_data)
        if base_layer_data and base_layer_data.strip()
        else "0x"
    )
    exec_hex = (
        normalize_input_payload_to_hex(execution_layer_data)
        if execution_layer_data and execution_layer_data.strip()
        else "0x"
    )

    nft_ref = nft_contract_address or "$test_nft_contract_address"
    app_ref = application_address or "$application_address"
    rpc_ref = rpc_url or "$rpc_url"

    owner_of_cast_command = _command(
        [
            "cast",
            "call",
            nft_ref,
            "ownerOf(uint256)(address)",
            token_id,
            "--rpc-url",
            rpc_ref,
        ]
    )

    balance_of_cast_command = _command(
        [
            "cast",
            "call",
            nft_ref,
            "balanceOf(address)(uint256)",
            balance_holder_ref,
            "--rpc-url",
            rpc_ref,
        ]
    )

    calldata_owner_of_command = _command(["cast", "calldata", "ownerOf(uint256)", token_id])
    if balance_holder_ref == "$holder_address":
        calldata_balance_of_shell = 'cast calldata "balanceOf(address)" "$holder_address"'
        calldata_balance_for_curl = calldata_balance_of_shell
    else:
        calldata_balance_of_shell = _command(
            ["cast", "calldata", "balanceOf(address)", balance_holder_ref]
        )
        calldata_balance_for_curl = calldata_balance_of_shell

    curl_owner_of_eth_call = (
        f"CALLDATA=$({calldata_owner_of_command}) && "
        f'curl -s -X POST "{rpc_ref}" -H "Content-Type: application/json" '
        '-d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"${nft_contract_address}\",\"data\":\"${CALLDATA}\"},\"latest\"],\"id\":1}"'
    )

    curl_balance_of_eth_call = (
        f"CALLDATA=$({calldata_balance_for_curl}) && "
        f'curl -s -X POST "{rpc_ref}" -H "Content-Type: application/json" '
        '-d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"${nft_contract_address}\",\"data\":\"${CALLDATA}\"},\"latest\"],\"id\":1}"'
    )

    safe_mint_command = _command(
        [
            "cast",
            "send",
            nft_ref,
            "safeMint(address,uint256,string)",
            "$receiver_address",
            token_id,
            token_uri,
            "--rpc-url",
            rpc_ref,
            "--private-key",
            owner_minter_private_key,
        ]
    )

    transfer_from_command = _command(
        [
            "cast",
            "send",
            nft_ref,
            "transferFrom(address,address,uint256)",
            "$from_address",
            "$to_address",
            token_id,
            "--rpc-url",
            rpc_ref,
            "--private-key",
            "$current_owner_private_key",
        ]
    )

    set_approval_for_all_command = _command(
        [
            "cast",
            "send",
            nft_ref,
            "setApprovalForAll(address,bool)",
            "$erc721_portal_address",
            "true",
            "--rpc-url",
            rpc_ref,
            "--private-key",
            depositor_key,
        ]
    )

    deposit_erc721_command = _command(
        [
            "cast",
            "send",
            "$erc721_portal_address",
            "depositERC721Token(address,address,uint256,bytes,bytes)",
            nft_ref,
            app_ref,
            token_id,
            base_hex,
            exec_hex,
            "--rpc-url",
            rpc_ref,
            "--private-key",
            depositor_key,
        ]
    )

    holder_address_from_key_command = _command(
        [
            "cast",
            "wallet",
            "address",
            "--private-key",
            depositor_key,
        ]
    )

    owner_address_from_key_command = _command(
        [
            "cast",
            "wallet",
            "address",
            "--private-key",
            owner_minter_private_key,
        ]
    )

    warnings: list[str] = []
    if application_address is None:
        warnings.append(
            "The application contract address is required before depositing. Obtain it from the running Cartesi application context."
        )
    if rpc_url is None:
        warnings.append(
            "The RPC URL is required. For stable v1.5.x the common default is `http://127.0.0.1:8545`; for versions that start with `2.0.0`, use the RPC URL from `cartesi run` output (not the example path `/anvil` unless your node exposes it)."
        )
    if nft_contract_address is None:
        warnings.append(
            "No NFT contract address was provided: use the CLI-provided TestNFT address from `cartesi address-book` unless the user specifies another ERC721."
        )
    warnings.append(
        "All `safeMint` transactions must be signed only with the first default dev private key: that wallet is the TestNFT owner and the only address authorized to mint."
    )
    if depositor_address is not None and str(depositor_address).strip():
        warnings.append(
            "When `depositor_address` is set, it must match the address derived from the depositor signing key (`holder_address_from_key_command`); otherwise ownership/balance reads and portal txs will disagree."
        )

    return {
        "status": "success",
        "summary": "Prepared host-side workflow for ERC721 deposits through ERC721Portal.",
        "data": {
            "execution_location": "Run these commands on the user's machine, not on this MCP server.",
            "version_guidance": _version_guidance(cli_track),
            "agent_workflow": [
                "Run `cartesi address-book` and record ERC721Portal and TestNFT (or user NFT) addresses.",
                "Ensure application logic can interpret the deposit (token contract address and `token_id`) using `base_layer_data` / `execution_layer_data` as needed.",
                "Configure depositor with `depositor_wallet_index`, `depositor_private_key`, and optionally `depositor_address` for read/balance calls. Resolve the signing address with `holder_address_from_key_command` when `depositor_address` is omitted. Export `nft_contract_address` in the shell when using curl one-liners.",
                "Verify ownership of `token_id` with `owner_of_cast_command` or `curl_owner_of_eth_call`. Compare the returned address to the depositor. Optionally check `balance_of_cast_command` or `curl_balance_of_eth_call` for how many NFTs the depositor holds.",
                "If the depositor does not own `token_id` and the id is free to mint, ask the user, then run `safe_mint_command` with `$receiver_address` set to the depositor address (from `depositor_address` or `holder_address_from_key_command`) — **only** the first default private key (`owner_minter_private_key`) may sign mints.",
                "If the NFT is held by another address (including the minter wallet), move it to the depositor with `transfer_from_command`: set `$from_address`, `$to_address` (depositor), and `$current_owner_private_key` to the current owner's key.",
                "With the depositor holding the NFT, run `set_approval_for_all_command` so ERC721Portal can operate on behalf of the depositor.",
                "Deposit via `deposit_erc721_command` using the depositor's private key.",
            ],
            "default_token_guidance": {
                "when_no_nft_specified": "Use TestNFT from `cartesi address-book`. Minting must use the first wallet in the local dev key bank (`owner_minter_private_key`).",
                "token_uri": "Used only for `safeMint`; adjust `token_uri` if the contract or user requires a specific metadata URI.",
            },
            "requirements": {
                "cast_install_check": [
                    "command -v cast",
                    "cast --version",
                ],
                "curl_install_check": [
                    "command -v curl",
                ],
                "required_values": [
                    "application_address",
                    "rpc_url",
                    "erc721_portal_address",
                    "nft_contract_address (or TestNFT from address-book)",
                    "token_id",
                    "depositor private key for setApprovalForAll and deposit",
                    "first default private key for safeMint only",
                ],
            },
            "rpc_url_guidance": {
                "stable_v1_5": "Usually `http://127.0.0.1:8545` for local dev.",
                "version_starts_with_2_0_0": "Use the RPC URL from `cartesi run` for the running application.",
            },
            "address_book_guidance": {
                "command": "cartesi address-book",
                "purpose": "Resolve ERC721Portal and TestNFT addresses.",
                "target_contracts": ["ERC721Portal", "TestNFT"],
            },
            "ownership_and_balance_checks": {
                "cast_templates": {
                    "owner_of_token_id": {
                        "description": "Returns the owner of `token_id` (read-only).",
                        "command_template": owner_of_cast_command,
                    },
                    "balance_of_address": {
                        "description": "ERC721 `balanceOf` for the depositor address (literal `depositor_address` when set, else the same address as `holder_address_from_key_command` / `$holder_address`).",
                        "command_template": balance_of_cast_command,
                    },
                },
                "curl_eth_call_templates": {
                    "notes": [
                        "These use JSON-RPC `eth_call`. Set shell variable `nft_contract_address` to the NFT contract (or substitute the literal address). `CALLDATA` is produced by `cast calldata` so the agent does not hand-encode the selector.",
                        "For `curl_balance_of_eth_call` without `depositor_address`, ensure `$holder_address` is set in the shell to the depositor address before running the calldata subcommand.",
                    ],
                    "owner_of_one_liner": curl_owner_of_eth_call,
                    "balance_of_one_liner": curl_balance_of_eth_call,
                    "calldata_helpers": {
                        "owner_of": calldata_owner_of_command,
                        "balance_of": calldata_balance_of_shell,
                    },
                },
            },
            "base_layer_data": {
                "original": base_layer_data,
                "normalized_hex": base_hex,
            },
            "execution_layer_data": {
                "original": execution_layer_data,
                "normalized_hex": exec_hex,
                "normalization_rule": "Same as input payload normalization; empty becomes `0x`.",
            },
            "token_id": {"value": token_id},
            "depositor_configuration": {
                "depositor_wallet_index": depositor_wallet_index,
                "depositor_private_key_source": "parameter" if (depositor_private_key and str(depositor_private_key).strip()) else "wallet_bank_index",
                "depositor_address_for_reads": depositor_address,
                "balance_check_uses_address": balance_holder_ref,
                "notes": [
                    "Use `depositor_wallet_index` to pick a different built-in dev wallet for setApprovalForAll and deposit.",
                    "Pass `depositor_private_key` to sign as a key outside the bank; it overrides `depositor_wallet_index`.",
                    "Pass `depositor_address` to pin balance/curl reads to a specific address; it must match the depositor signer address or reads and txs will disagree.",
                ],
            },
            "private_keys": {
                "owner_minter_only_for_safe_mint": owner_minter_private_key,
                "depositor_signer": depositor_key,
                "all_default_local_private_keys": private_keys,
                "usage_guidance": "Never sign `safeMint` with a key other than `owner_minter_only_for_safe_mint` (first key). Use `depositor_signer` for setApprovalForAll and deposit; use other keys only as `current_owner_private_key` for `transferFrom` when moving the NFT to the depositor.",
            },
            "holder_address_from_key_command": holder_address_from_key_command,
            "owner_address_from_key_command": owner_address_from_key_command,
            "cast_command_templates": {
                "safe_mint_to_receiver": safe_mint_command,
                "transfer_from": transfer_from_command,
                "set_approval_for_all_erc721_portal": set_approval_for_all_command,
                "deposit_erc721_token": deposit_erc721_command,
            },
            "requested_input": {
                "application_address": application_address,
                "token_id": token_id,
                "token_uri": token_uri,
                "nft_contract_address": nft_contract_address,
                "base_layer_data": base_layer_data,
                "execution_layer_data": execution_layer_data,
                "rpc_url": rpc_url,
                "depositor_wallet_index": depositor_wallet_index,
                "depositor_private_key_provided": bool(depositor_private_key and str(depositor_private_key).strip()),
                "depositor_address": depositor_address,
                "project_path": project_path,
            },
        },
        "warnings": warnings,
        "next_steps": [
            "Run `command -v cast`, `cast --version`, and `command -v curl` on the user's machine.",
            f"Change into the project directory if needed: `{project_path}`.",
            "Run `cartesi address-book` and set ERC721Portal, TestNFT (or chosen NFT), and RPC URL.",
            f"Confirm depositor address (configured or via `{holder_address_from_key_command}`) matches balance/ownership checks.",
            f"Check ownership: `{owner_of_cast_command}` or use the curl one-liner in `ownership_and_balance_checks.curl_eth_call_templates`.",
            f"If needed, mint with `{safe_mint_command}` (first-key / owner only), then `{transfer_from_command}` if the NFT must move to the depositor.",
            f"Approve portal: `{set_approval_for_all_command}`.",
            f"Deposit: `{deposit_erc721_command}`.",
        ],
    }


