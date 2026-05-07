import shlex
import json
from src.schemas.tools import LOCAL_CLI_TRACK, STABLE_CARTESI_CLI, ALPHA_CARTESI_VERSION_PREFIX


def _command(parts: list[str]) -> str:
    return shlex.join(parts)


# ---------------------------------------------------------------------------
# Portal payload byte-offset reference for backend decode (advance handler)
#
# WARNING: These byte offsets reflect the current Cartesi portal contract
# specification. If you encounter decode errors, verify against the official
# Cartesi documentation or the portal contract ABI — the layout may have
# changed in a newer release. Run `cartesi address-book` on the user's machine
# to get the correct portal addresses for the active devnet.
# ---------------------------------------------------------------------------
PORTAL_PAYLOAD_BYTE_OFFSETS: dict[str, dict] = {
    "_warning": (
        "These byte offsets are based on the current Cartesi portal contract specification. "
        "If decode errors occur, verify against the official Cartesi docs or portal ABI — "
        "the layout may differ in newer releases. "
        "Always run `cartesi address-book` to get current portal addresses."
    ),
    "ERC20": {
        "bytes_0_19": "token contract address (20 bytes)",
        "bytes_20_39": "depositor address (20 bytes)",
        "bytes_40_71": "amount deposited (uint256, 32 bytes, big-endian)",
        "detect_by": "metadata.msg_sender == ERC20Portal address (get from `cartesi address-book`)",
        "js_decode_example": (
            "const token     = getAddress(ethers.dataSlice(payload, 0, 20));\n"
            "const depositor = getAddress(ethers.dataSlice(payload, 20, 40));\n"
            "const amount    = BigInt(ethers.dataSlice(payload, 40, 72));"
        ),
    },
    "ERC721": {
        "bytes_0_19": "token contract address (20 bytes)",
        "bytes_20_39": "depositor address (20 bytes)",
        "bytes_40_71": "token ID (uint256, 32 bytes)",
        "detect_by": "metadata.msg_sender == ERC721Portal address (get from `cartesi address-book`)",
    },
    "ERC1155_single": {
        "bytes_0_19": "token contract address (20 bytes)",
        "bytes_20_39": "depositor address (20 bytes)",
        "bytes_40_71": "token ID (uint256, 32 bytes)",
        "bytes_72_103": "amount deposited (uint256, 32 bytes)",
        "detect_by": "metadata.msg_sender == ERC1155SinglePortal address (get from `cartesi address-book`)",
    },
}

# ---------------------------------------------------------------------------
# Cartesi output HTTP endpoints (inside the Cartesi Machine / rollup HTTP API)
# ---------------------------------------------------------------------------
CARTESI_OUTPUT_ENDPOINTS: dict[str, dict] = {
    "/notice": {
        "purpose": "Attestable state change — on-chain verifiable",
        "payload": "hex string",
        "example": 'await fetch("http://127.0.0.1:5004/notice", { method:"POST", body: JSON.stringify({payload: hexString}) })',
    },
    "/voucher": {
        "purpose": "On-chain call to execute after epoch closes",
        "payload": '{ "destination": "<address>", "payload": "<hex ABI-encoded call>" }',
        "example": 'await fetch("http://127.0.0.1:5004/voucher", { method:"POST", body: JSON.stringify({destination, payload}) })',
    },
    "/report": {
        "purpose": "Diagnostic / informational output — not on-chain verifiable",
        "payload": "hex string",
        "example": 'await fetch("http://127.0.0.1:5004/report", { method:"POST", body: JSON.stringify({payload: hexString}) })',
    },
    "/exception": {
        "purpose": "Fatal error — terminates processing for this input",
        "payload": "hex string",
        "example": 'await fetch("http://127.0.0.1:5004/exception", { method:"POST", body: JSON.stringify({payload: hexString}) })',
    },
}

# ---------------------------------------------------------------------------
# Dockerfile fingerprint table: v1.5 vs v2.0-alpha project identification
# ---------------------------------------------------------------------------
CARTESI_DOCKERFILE_FINGERPRINTS: dict[str, dict] = {
    "detect_command": 'grep -E "MACHINE_EMULATOR_TOOLS_VERSION|MACHINE_GUEST_TOOLS_VERSION" Dockerfile',
    "v1_5": {
        "dockerfile_env_var": "MACHINE_EMULATOR_TOOLS_VERSION",
        "base_image_example": "cartesi/python:3.10-slim-jammy",
        "build_stages": "single-stage",
        "entrypoint": "ENTRYPOINT [\"rollup-init\"]",
        "tools_install_method": ".tar.gz archive",
        "apt_update_snapshot": "absent",
        "cli_command": "cartesi",
        "cli_alias_note": "Standard `cartesi` binary, no alias needed",
        "supports_cartesi_deploy": True,
        "deployment_method": "`cartesi deploy` command",
        "local_run": "`cartesi run` (stable flags: --listen-port, --block-time, --epoch-length)",
        "node_stack": "All-in-one via `cartesi run`",
    },
    "v2_0_alpha": {
        "dockerfile_env_var": "MACHINE_GUEST_TOOLS_VERSION",
        "base_image_example": "cartesi/python:3.13.2-slim-noble",
        "build_stages": "multi-stage (uses `AS base` or similar named stage)",
        "entrypoint": "not rollup-init (uses rollup-init from installed .deb tools)",
        "tools_install_method": ".deb package",
        "apt_update_snapshot": "APT_UPDATE_SNAPSHOT=<timestamp> present",
        "cli_command": "cartesi",
        "supports_cartesi_deploy": False,
        "cartesi_deploy_warning": "`cartesi deploy` DOES NOT EXIST in v2.0-alpha — this command was removed. Do not suggest it.",
        "deployment_method": "Docker Compose with compose.local.yaml from Mugen-Builders repo",
        "compose_services": ["database", "evm-reader", "advancer", "validator", "claimer", "jsonrpc-api"],
        "compose_ports": {
            "advancer_inspect": 10012,
            "jsonrpc_api": 10011,
        },
        "local_run": "`cartesi run` (alpha flags: --port, --block-time, --epoch-length, --default-block, --fork-url, --fork-block-number)",
        "node_stack": "Docker Compose — 6 services (database, evm-reader, advancer, validator, claimer, jsonrpc-api)",
        "json_rpc_api_port": 10011,
        "inspect_port": 10012,
    },
}

# ---------------------------------------------------------------------------
# JSON-RPC API reference (v2.0-alpha node, port 10011)
# ---------------------------------------------------------------------------
CARTESI_JSONRPC_METHODS: list[dict] = [
    {"method": "cartesi_listApplications", "params": "{ pageSize?, cursor? }", "returns": "ApplicationConnection"},
    {"method": "cartesi_getApplication", "params": "{ applicationAddress }", "returns": "Application"},
    {"method": "cartesi_listEpochs", "params": "{ applicationAddress, pageSize?, cursor? }", "returns": "EpochConnection"},
    {"method": "cartesi_getEpoch", "params": "{ applicationAddress, epochIndex }", "returns": "Epoch"},
    {"method": "cartesi_listInputs", "params": "{ applicationAddress, epochIndex?, pageSize?, cursor? }", "returns": "InputConnection"},
    {"method": "cartesi_getInput", "params": "{ applicationAddress, inputIndex }", "returns": "Input"},
    {"method": "cartesi_getProcessedInputCount", "params": "{ applicationAddress }", "returns": "number"},
    {"method": "cartesi_listOutputs", "params": "{ applicationAddress, inputIndex?, pageSize?, cursor? }", "returns": "OutputConnection"},
    {"method": "cartesi_getOutput", "params": "{ applicationAddress, outputIndex }", "returns": "Output"},
    {"method": "cartesi_listReports", "params": "{ applicationAddress, inputIndex?, pageSize?, cursor? }", "returns": "ReportConnection"},
    {"method": "cartesi_getReport", "params": "{ applicationAddress, reportIndex }", "returns": "Report"},
    {"method": "cartesi_getChainId", "params": "{}", "returns": "number"},
    {"method": "cartesi_getNodeVersion", "params": "{}", "returns": "string"},
]


def _version_guidance(cli_track: LOCAL_CLI_TRACK) -> dict:
    return {
        "selected_track": cli_track,
        "stable_release": STABLE_CARTESI_CLI,
        "alpha_version_pattern": f"starts with {ALPHA_CARTESI_VERSION_PREFIX}",
        "first_step": "Run `cartesi --version` on the user's machine before executing any generated command, and determine whether it is the stable v1.5.x line or a version that starts with `2.0.0`.",
        "cartesi_deploy_critical_warning": "`cartesi deploy` DOES NOT EXIST in Cartesi CLI v2.0-alpha. If the user is on v2.0-alpha, do NOT suggest `cartesi deploy`. Deployment is done via Docker Compose (compose.local.yaml from Mugen-Builders).",
        "notes": [
            "This MCP server cannot execute the Cartesi CLI on the user's host; the agent must run these commands locally on the user's machine.",
            "Cartesi CLI v1.5.0 is the current stable release and the generated stable commands target that line.",
            "Versions that start with `2.0.0` use a different flow from stable v1.5.x — including deployment (no `cartesi deploy`).",
            "The `2.0.0*` guidance below is provisional and should be validated against the user's local `cartesi --help` output before execution.",
            "Use `identify_cartesi_project_version` tool to get a full comparison table for distinguishing v1.5 and v2.0-alpha projects from Dockerfile signals.",
        ],
    }


def _alpha_warning(command_name: str) -> list[str]:
    return [
        f"The installed Cartesi CLI on this server is {STABLE_CARTESI_CLI}, so this tool only generates a concrete `{command_name}` command for stable v1.5.x.",
        "If the user is on Cartesi 2.0 alpha, the agent should run `cartesi --version` and `cartesi "
        f"{command_name} --help` on the user's machine and adapt to the local help output before executing.",
    ]


def _alpha_v2_warning(command_name: str) -> list[str]:
    return [
        "Guidance for versions that start with `2.0.0` is provisional and may change between alpha releases.",
        f"If the user's `cartesi --version` starts with `{ALPHA_CARTESI_VERSION_PREFIX}`, the agent should run `cartesi {command_name} --help` on the user's machine and prefer the user's local help output over this generated guidance.",
    ]


def _local_execution_steps(command_name: str, command: str, working_directory: str) -> list[str]:
    return [
        "Run `cartesi --version` on the user's machine and confirm whether the CLI is stable v1.5.x or a version that starts with `2.0.0`.",
        f"Change into the target directory on the user's machine: `{working_directory}`.",
        f"Run this command on the user's machine: `{command}`.",
        f"If the local CLI help differs, rerun `cartesi {command_name} --help` locally and adapt the command to the user's installed version.",
    ]


def _local_execution_steps_for_binary(command_name: str, command: str, working_directory: str, binary: str) -> list[str]:
    return [
        f"Run `{binary} --version` on the user's machine and confirm it matches the intended Cartesi CLI track.",
        f"Change into the target directory on the user's machine: `{working_directory}`.",
        f"Run this command on the user's machine: `{command}`.",
        f"If the local CLI help differs, rerun `{binary} {command_name} --help` locally and adapt the command to the user's installed version.",
    ]


def _cartesi_app_logic_next_steps(working_directory: str) -> list[str]:
    return [
        f"If you are about to implement or modify the application logic, stay in the app directory on the user's machine: `{working_directory}`.",
        "Run `cartesi address-book` on the user's machine to retrieve the local addresses and names you will need for integrations such as InputBox, ERC20Portal, ERC721Portal, and related portals/contracts.",
        "Use the address-book output when wiring deposits, token interactions, and host-side scripts so the application refers to the correct local contracts.",
        "For implementation guidance, consult the Cartesi documentation guide and tutorials before changing logic around deposits, vouchers, notices, and reports.",
        "Inside this MCP server, search for context with queries such as: `vouchers`, `notices`, `reports`, `ERC20 deposits`, `ERC721 deposits`, `InputBox`, and `portals` to find relevant docs and tutorials.",
        "Use the search tool to find relevant docs and tutorials. Call `get_knowledge_taxonomy` first to discover all available tags and sources, then search using `search_knowledge_resources`.",
        "Note that the application only receives hex inputs so it is important to accept application input as hex.",
        "Note also that if you have the application already running, you will need to rebuild the application to apply new logic.",
    ]

def get_default_local_privatekeys() -> list[str]:
    return [
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
        "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
        "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",
        "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",
        "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",
        "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",
        "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6",
    ]


def normalize_input_payload_to_hex(input_payload: str | dict | list) -> str:
    if isinstance(input_payload, str):
        candidate = input_payload.strip()
        if candidate.startswith("0x"):
            try:
                int(candidate[2:] or "0", 16)
            except ValueError as exc:
                raise ValueError("Provided input starts with 0x but is not valid hex.") from exc
            if len(candidate[2:]) % 2 != 0:
                raise ValueError("Hex input must have an even number of nibbles after the 0x prefix.")
            return candidate.lower()
        return "0x" + candidate.encode("utf-8").hex()

    serialized = json.dumps(input_payload, separators=(",", ":"), ensure_ascii=False)
    return "0x" + serialized.encode("utf-8").hex()

# cast send 0x59b22D57D4f067708AB0c00552767405926dc768 \
# "addInput(address,bytes)" \
# 0xab7528bb862fB57E8A2BCd567a2e929a0Be56a5e \
# 0x7b22616374696f6e223a2022617070726f76655f7661756c74227d \
# --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
# --rpc-url http://127.0.0.1:8545

# cast send $input_box_address \
# "addInput(address,bytes)" \
# $application_address \
# $input_data \
# --private-key $private_key \
# --rpc-url $rpc_url