import networkx as nx

from .models import SupplierDependency, SupplierProfile


def build_supplier_graph(
    suppliers: list[SupplierProfile],
    dependencies: list[SupplierDependency],
) -> nx.DiGraph:
    """
    Build a directed supplier dependency graph.

    Nodes = suppliers
    Edges = supplier dependencies
    """

    graph = nx.DiGraph()

    for supplier in suppliers:
        graph.add_node(
            supplier.id,
            name=supplier.name,
            strategic_importance=supplier.strategic_importance,
            distress_score=supplier.distress_score or 0.0,
        )

    for dependency in dependencies:
        graph.add_edge(
            dependency.source_supplier_id,
            dependency.target_supplier_id,
            dependency_type=dependency.dependency_type,
            dependency_weight=dependency.dependency_weight,
            disruption_impact=dependency.disruption_impact,
        )

    return graph


def calculate_centrality(graph: nx.DiGraph) -> dict[str, float]:
    """
    Calculate degree centrality for every supplier.

    NetworkX normalizes degree centrality based on graph connectivity.
    """

    if graph.number_of_nodes() == 0:
        return {}

    centrality = nx.degree_centrality(graph)

    # Convert 0-1-ish values to the 0-100 scale used by the PRD.
    return {
        supplier_id: min(100.0, score * 100)
        for supplier_id, score in centrality.items()
    }


def find_affected_suppliers(
    graph: nx.DiGraph,
    supplier_id: str,
) -> list[str]:
    """
    Traverse downstream dependencies using BFS.

    The PRD explicitly identifies BFS/DFS as appropriate for
    cascading-risk propagation.
    """

    if supplier_id not in graph:
        return []

    affected = []
    visited = set([supplier_id])
    queue = [supplier_id]

    while queue:
        current = queue.pop(0)

        for neighbor in graph.successors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                affected.append(neighbor)
                queue.append(neighbor)

    return affected