from pathlib import Path

from babel.messages.frontend import compile_catalog


def compile_catalogs():
    cmd = compile_catalog()
    cmd.domain = "messages"  # Specify the domain
    cmd.directory = str(Path(__file__).parent / "translations")  # Ensure directory is a string
    cmd.statistics = True
    cmd.use_fuzzy = False  # Disable fuzzy matching for more accurate results
    cmd.finalize_options()
    cmd.run()
