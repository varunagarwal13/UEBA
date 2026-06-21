from datetime import datetime, timedelta

from src.common.schema import Event
from src.profile.build import (
    build_profiles,
    build_user_profile,
    hour_of_day_likelihood,
)
from src.profile.graph import build_entity_graph


def _event(user_id, hour, event_type="http", resource=None, command=None, day=6):
    return Event(
        user_id=user_id,
        timestamp=datetime(2025, 3, day, hour, 0, 0),
        event_type=event_type,
        action="x",
        resource=resource,
        raw={"Command": command} if command else None,
    )


def test_hour_and_dow_distributions_sum_to_one():
    events = [_event("camilo", h) for h in [9, 9, 14, 22]]
    profile = build_user_profile("camilo", events)

    assert len(profile.hour_of_day_dist) == 24
    assert abs(sum(profile.hour_of_day_dist) - 1.0) < 1e-9
    assert len(profile.day_of_week_dist) == 7
    assert abs(sum(profile.day_of_week_dist) - 1.0) < 1e-9


def test_smoothing_avoids_zero_probability_for_unseen_hour():
    events = [_event("camilo", 9)]
    profile = build_user_profile("camilo", events)

    # camilo never logged in at hour 3, but smoothing keeps it > 0
    assert hour_of_day_likelihood(profile, 3) > 0
    # the hour he did use should still be more likely than an unused one
    assert hour_of_day_likelihood(profile, 9) > hour_of_day_likelihood(profile, 3)


def test_command_exec_uses_command_as_access_key():
    events = [_event("camilo", 9, event_type="command_exec", command="whoami")]
    profile = build_user_profile("camilo", events)

    assert profile.access_counts.get("cmd:whoami") == 1


def test_resource_events_use_resource_as_access_key():
    events = [_event("camilo", 9, event_type="file_op", resource="/etc/passwd")]
    profile = build_user_profile("camilo", events)

    assert profile.access_counts.get("res:/etc/passwd") == 1


def test_pivot_account_flagged_in_profile():
    profile = build_user_profile("ubuntu", [_event("ubuntu", 9)])
    assert profile.is_pivot_account

    profile2 = build_user_profile("camilo", [_event("camilo", 9)])
    assert not profile2.is_pivot_account


def test_inter_event_stats_need_at_least_two_gaps():
    # one event -> no gaps at all
    p1 = build_user_profile("camilo", [_event("camilo", 9)])
    assert p1.inter_event_seconds_mean is None

    # two events -> one gap, mean known but std needs two gaps
    e1 = _event("camilo", 9)
    e2 = Event(user_id="camilo", timestamp=e1.timestamp + timedelta(seconds=60),
                event_type="http", action="x")
    p2 = build_user_profile("camilo", [e1, e2])
    assert p2.inter_event_seconds_mean == 60.0
    assert p2.inter_event_seconds_std is None


def test_build_profiles_groups_by_user():
    events = [_event("camilo", 9), _event("camilo", 10), _event("irene", 14)]
    profiles = build_profiles(events)

    assert set(profiles.keys()) == {"camilo", "irene"}
    assert profiles["camilo"].n_events == 2
    assert profiles["irene"].n_events == 1


def test_entity_graph_edge_weights():
    events = [
        _event("camilo", 9, event_type="file_op", resource="/etc/passwd"),
        _event("camilo", 10, event_type="file_op", resource="/etc/passwd"),
        _event("irene", 11, event_type="file_op", resource="/etc/passwd"),
    ]
    g = build_entity_graph(events)

    assert g["user:camilo"]["res:/etc/passwd"]["weight"] == 2
    assert g["user:irene"]["res:/etc/passwd"]["weight"] == 1
    assert g.nodes["user:camilo"]["bipartite"] == "user"
    assert g.nodes["res:/etc/passwd"]["bipartite"] == "resource"
