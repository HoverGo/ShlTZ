import pytest
from cacheops.conf import settings as cacheops_settings


@pytest.fixture(autouse=True)
def disable_cacheops(settings):
    settings.CACHEOPS_ENABLED = False
    cacheops_settings.CACHEOPS_ENABLED = False
    yield
    cacheops_settings.CACHEOPS_ENABLED = False

