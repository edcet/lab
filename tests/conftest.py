import pytest_asyncio

pytest_plugins = ['pytest_asyncio']

# Set the default fixture loop scope to 'function' to avoid deprecation warnings
pytest_asyncio.plugin.asyncio_default_fixture_loop_scope = 'function'
