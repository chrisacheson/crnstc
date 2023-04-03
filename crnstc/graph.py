class Graph:
    def __init__(self):
        self.nodes = dict()
        self.node_data = dict()
        self.edges = dict()

    def add_node(self, key, data=None):
        self.nodes[key] = set()
        if data:
            self.node_data[key] = data

    def remove_node(self, key):
        for other in self.nodes[key]:
            self.remove_edge(key, other)
            del self.nodes[key]
            self.node_data.pop(key, None)

    @staticmethod
    def edge_key(a, b):
        if a < b:
            return a, b
        else:
            return b, a

    def add_edge(self, a, b, data=None):
        if a not in self.nodes:
            self.add_node(a)

        if b not in self.nodes:
            self.add_node(b)

        self.nodes[a].add(b)
        self.nodes[b].add(a)

        key = self.edge_key(a, b)
        self.edges[key] = data

    def remove_edge(self, a, b):
        self.nodes[a].remove(b)
        self.nodes[b].remove(a)
        key = self.edge_key(a, b)
        del self.edges[key]

    def __str__(self):
        ind = " " * 4
        nodes_str = list()
        edges_str = list()

        for node in self.nodes:
            node_str = f"{ind * 2}{node}"

            if node in self.node_data:
                node_str += f": {self.node_data[node]}"

            nodes_str.append(node_str)

        for edge, data in self.edges.items():
            edge_str = f"{ind * 2}{edge}"

            if data:
                edge_str += f": {data}"

            edges_str.append(edge_str)

        nodes_str = "\n".join(nodes_str)
        edges_str = "\n".join(edges_str)

        return "\n".join((
            f"{self.__class__.__name__}(",
            f"{ind}{len(self.nodes)} nodes:",
            nodes_str,
            f"{ind}{len(self.edges)} edges:",
            edges_str,
            ")",
        ))
