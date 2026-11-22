# -*- coding: utf-8 -*-

"""
Generate agentcore/agentcore.json, agentcore/aws-targets.json, and agentcore_app/<Runtime>/
from the config, uv.lock, and the package.
"""

from agent_app.agentcore_project.gen import main


if __name__ == "__main__":
    main()
