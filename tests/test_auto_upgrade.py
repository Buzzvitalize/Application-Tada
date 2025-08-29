import importlib

def test_ensure_admin_always_runs_upgrade(monkeypatch):
    app_module = importlib.import_module('app')
    called = {}
    def fake_upgrade():
        called['yes'] = True
    monkeypatch.setattr(app_module, 'upgrade', fake_upgrade)
    app_module.ensure_admin()
    assert called.get('yes') is True
