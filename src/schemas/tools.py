from typing import Literal

STABLE_CARTESI_CLI = "1.5.0"
ALPHA_CARTESI_VERSION_PREFIX = "2.0.0"
LOCAL_CLI_TRACK = Literal["stable-1.5.x", "alpha-2.x", "unknown"]
STABLE_CREATE_TEMPLATES = (
    "cpp",
    "cpp-low-level",
    "go",
    "javascript",
    "lua",
    "python",
    "ruby",
    "rust",
    "typescript",
)
STABLE_OPTIONAL_RUN_SERVICES = {"bundler", "explorer", "paymaster"}
ALPHA_CREATE_TEMPLATES = (
    "cpp",
    "cpp-low-level",
    "go",
    "java",
    "javascript",
    "lua",
    "python",
    "ruby",
    "rust",
    "typescript",
)
ALPHA_OPTIONAL_RUN_SERVICES = {"bundler", "espresso", "explorer", "graphql", "paymaster"}
