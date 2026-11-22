# -*- coding: utf-8 -*-

"""
Audit a dataset's sessions with the local agent, one conversation each, and
write the predictions. Calls the model: every session is paid for.
"""

from agent_app.devtools.evaluation import main

if __name__ == "__main__":
    main()
