import time


def ok_provider(cfg, prev):
    return {
        "ok": True,
        "kind": "quota",
        "data": {
            "quotas": [
                {
                    "id": "q",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "week", "label": "Semana"},
                    "used_percent": 10,
                }
            ]
        },
    }


def fail_provider(cfg, prev):
    return {"ok": False, "error": {"code": "timeout", "message_key": "timeout"}, "data": None}


def fail_network_provider(cfg, prev):
    return {"ok": False, "error": {"code": "network", "message_key": "network"}, "data": None}


def boom_provider(cfg, prev):
    raise RuntimeError("boom")


def hang_provider(cfg, prev):
    time.sleep(30)
    return {"ok": True, "kind": "quota", "data": {"quotas": []}}


def counting_provider(cfg, prev):
    return {
        "ok": True,
        "kind": "quota",
        "data": {
            "quotas": [
                {
                    "id": "c",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "week", "label": "Semana"},
                    "used_percent": 1,
                }
            ]
        },
    }


def metered_ok_provider(cfg, prev):
    return {
        "ok": True,
        "kind": "metered",
        "data": {
            "quotas": [],
            "money": {
                "currency": "USD",
                "spend": [
                    {
                        "period": {"id": "2026-11", "label": "Novembro"},
                        "amount": "12.40",
                    }
                ],
            },
        },
    }


def bad_provider_leaks_secret(cfg, prev):
    return {
        "ok": True,
        "kind": "quota",
        "data": {
            "quotas": [
                {
                    "id": "q",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "week", "label": "Semana"},
                    "used_percent": 5,
                }
            ],
            "raw_token": "FAKE_TEST_SECRET_DO_NOT_USE",
        },
    }


def bad_provider_invalid_percent(cfg, prev):
    return {
        "ok": True,
        "kind": "quota",
        "data": {
            "quotas": [
                {
                    "id": "q",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "week", "label": "Semana"},
                    "used_percent": -1,
                }
            ]
        },
    }


def codex_3600_provider(cfg, prev):
    return {
        "ok": True,
        "kind": "quota",
        "data": {
            "quotas": [
                {
                    "id": "account_primary",
                    "scope": {"type": "account", "id": "account", "label": "Conta"},
                    "window": {"id": "rolling_1h", "label": "1 hora", "duration_seconds": 3600},
                    "used_percent": 22,
                }
            ]
        },
    }
