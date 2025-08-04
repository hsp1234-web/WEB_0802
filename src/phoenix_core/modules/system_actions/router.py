# -*- coding: utf-8 -*-

# This file ensures the system_actions_router is discovered by the application startup process.
# It follows the established pattern of a module in the `modules` directory
# importing the actual router definition from the `api` directory.

from src.phoenix_core.api import system_actions_router

# The router registers itself to the global registry in its own file.
# The presence of this file and the import statement are sufficient to trigger discovery.
