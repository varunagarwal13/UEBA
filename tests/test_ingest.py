from src.ingest.spedia import (
    PIVOT_ACCOUNTS,
    baseline_and_campaign_split,
    load_spedia,
)


def test_load_spedia_basic_shape():
    events, labels = load_spedia("tests/fixtures/sample_spedia.csv")

    assert len(events) == 5
    assert len(labels) == 5
    # events come back sorted by timestamp -- humberto (13:14:35) is
    # genuinely earlier than camilo (13:15:10) on the same day
    assert events[0].user_id == "humberto"
    assert events[0].timestamp.day == 6
    assert events[1].user_id == "camilo"


def test_anomaly_label_never_leaks_into_event():
    events, _ = load_spedia("tests/fixtures/sample_spedia.csv")
    for e in events:
        assert "Anomaly" not in (e.raw or {})
        assert not hasattr(e, "anomaly")


def test_event_type_inference():
    events, _ = load_spedia("tests/fixtures/sample_spedia.csv")
    types = {e.user_id: e.event_type for e in events}
    assert types["humberto"] == "login"
    assert types["camilo"] in ("command_exec", "email_send")  # camilo has two rows


def test_pivot_account_flagged_in_labels():
    _, labels = load_spedia("tests/fixtures/sample_spedia.csv")
    ubuntu_row = labels[labels["user_id"] == "ubuntu"].iloc[0]
    assert ubuntu_row["is_pivot_account"]
    assert "ubuntu" in PIVOT_ACCOUNTS

    irene_row = labels[labels["user_id"] == "irene"].iloc[0]
    assert not irene_row["is_pivot_account"]


def test_baseline_campaign_split():
    _, labels = load_spedia("tests/fixtures/sample_spedia.csv")
    baseline_ids, campaign_ids = baseline_and_campaign_split(labels)

    # the two March 6 rows (camilo, humberto) are baseline
    assert len(baseline_ids) == 2
    # the two March 23 rows (irene, ubuntu) + March 25 (camilo) are campaign
    assert len(campaign_ids) == 3
