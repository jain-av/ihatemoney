import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, context):
        sys.path.insert(0, "./ihatemoney")
        from babel_utils import compile_catalogs

        compile_catalogs()
