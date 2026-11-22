# -*- coding: utf-8 -*-

from pathlib import Path

_dir_here = Path(__file__).absolute().parent
PACKAGE_NAME = _dir_here.name


class PathEnum:
    """
    Every project path the code reads or writes, as an absolute path, so nothing
    depends on the current directory.

    An entry is added together with its first reader, never ahead of it: a path
    nobody reads ends up pointing at a directory that no longer exists.
    """

    dir_project_root = _dir_here.parent

    # Source Code
    dir_package = _dir_here
    path_mise_toml = dir_project_root / "mise.toml"
    path_quick_links_md = dir_project_root / "QUICK_LINKS.md"

    # The audit data bundled with the package, read by one.audit_store and
    # written by `mise run sync-audit-data`
    dir_audit_data = dir_package / "audit" / "data"

    # Config files, see Config.load_from_local_config_file
    dir_config = dir_project_root / "config"

    # AgentCore CLI project, see the agentcore_project subpackage
    dir_agentcore = dir_project_root / "agentcore"
    path_agentcore_json = dir_agentcore / "agentcore.json"
    path_aws_targets_json = dir_agentcore / "aws-targets.json"
    path_agentcore_cdk_stack_ts = dir_agentcore / "cdk" / "lib" / "cdk-stack.ts"
    # agentcore_app/<Runtime>/, the codeLocation of each runtime, assembled by ac-gen.
    # Not ``app/``, the AgentCore CLI's default: that directory is the Next.js App Router.
    dir_agentcore_app = dir_project_root / "agentcore_app"

    # The runs of `mise run eval-run`, one directory each; under tmp/, so not in Git
    dir_eval = dir_project_root / "tmp" / "eval"

    # Test
    dir_htmlcov = dir_project_root / "htmlcov"


path_enum = PathEnum()
"""
Single entry point for all project paths with absolute path references.
"""
