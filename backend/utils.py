def generate_mermaid_diagram(graph):
    """Generate horizontal Mermaid diagram for the workflow"""
    print(graph.get_graph().draw_mermaid())
