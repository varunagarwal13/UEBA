"""
Bipartite user <-> resource entity graph, weighted by interaction
frequency. Feeds subgraph anomaly scoring and any graph-based features
HDBSCAN wants later.

Uses the same _access_key logic as the per-user profile, so "resource"
means the same thing in both places: a command for command_exec
events, the Event.resource field for everything else.
"""

from typing import List

import networkx as nx

from src.common.schema import Event
from src.profile.build import _access_key


def build_entity_graph(events: List[Event]) -> nx.Graph:
    """Returns a NetworkX graph with two node types (bipartite="user"
    / bipartite="resource") and weighted edges counting interactions.
    Events with no derivable access key (e.g. a plain login) don't
    contribute an edge."""
    g = nx.Graph()
    for e in events:
        key = _access_key(e)
        if key is None:
            continue
        user_node = f"user:{e.user_id}"
        resource_node = key  # already prefixed cmd: or res:

        g.add_node(user_node, bipartite="user")
        g.add_node(resource_node, bipartite="resource")

        if g.has_edge(user_node, resource_node):
            g[user_node][resource_node]["weight"] += 1
        else:
            g.add_edge(user_node, resource_node, weight=1)

    return g
