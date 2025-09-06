from src.infra.monitoring import healthcheck

def test_health():
    assert healthcheck()['ok'] is True
