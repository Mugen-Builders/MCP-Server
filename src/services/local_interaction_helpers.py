import shlex
from src.schemas.tools import LOCAL_CLI_TRACK, STABLE_CARTESI_CLI, ALPHA_CARTESI_VERSION_PREFIX


def _command(parts: list[str]) -> str:
    return shlex.join(parts)


def _version_guidance(cli_track: LOCAL_CLI_TRACK) -> dict:
    return {
        "selected_track": cli_track,
        "stable_release": STABLE_CARTESI_CLI,
        "alpha_version_pattern": f"starts with {ALPHA_CARTESI_VERSION_PREFIX}",
        "first_step": "Run `cartesi --version` on the user's machine before executing any generated command, and determine whether it is the stable v1.5.x line or a version that starts with `2.0.0`.",
        "notes": [
            "This MCP server cannot execute the Cartesi CLI on the user's host; the agent must run these commands locally on the user's machine.",
            "Cartesi CLI v1.5.0 is the current stable release and the generated stable commands target that line.",
            "Versions that start with `2.0.0` use a different flow from stable v1.5.x.",
            "The `2.0.0*` guidance below is provisional and should be validated against the user's local `cartesi --help` output before execution.",
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

