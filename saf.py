class SAF(object):
    def __init__(self, saf):
        self.saf = saf
        self._tokens = {t['id']: t for t in saf['tokens']}

    def get_token(self, token_id):
        return self._tokens[token_id]

    def get_children(self, token):
        if not isinstance(token, int): token = token['id']
        return ((rel['relation'], self.get_token(rel['child']))
                for rel in self.saf['dependencies'] if rel['parent'] == token)

    def __getattr__(self, attr):
        try:
            return self.saf[attr]
        except KeyError:
            return object.__getattribute__(self, attr)

    def get_tokens(self, sentence):
        return sorted((t for t in self.saf['tokens'] if t['sentence'] == sentence),
                      key = lambda t: int(t['offset']))


    def get_root(self, sentence):
        parents = {d['child'] : d['parent'] for d in self.saf['dependencies']
                   if self.get_token(d['child'])['sentence'] == sentence}
        # root is a parent that has no parents
        roots = set(parents.values()) - set(parents.keys())
        if len(roots) != 1:
            raise ValueError("Sentence {sentence} has roots {roots}".format(**locals()))
        return self.get_token(list(roots)[0])

    def get_sentences(self):
        return sorted({t['sentence'] for t in self.saf['tokens']})

    def get_node_depths(self, sentence):
        # return a dict with the dept of each node
        rels = [d for d in self.saf['dependencies']
            if self.get_token(d['child'])['sentence'] == sentence]
        generations = {self.get_root(sentence)['id'] : 0}
        changed = True
        while changed:
            changed = False
            for rel in rels:
                if rel['child'] not in generations and rel['parent'] in generations:
                    generations[rel['child']] = generations[rel['parent']] + 1
                    changed = True
        return generations

    def get_descendants(self, node, exclude=None):
        """
        Yield all descendants (including the node itself),
        stops when a node in exclude is reached
        @param exlude: a set of nodes to exclude
        """
        if isinstance(node, int): node = self.get_token(node)
        if exclude is None: exclude = set()
        if node['id'] in exclude: return
        exclude.add(node['id'])
        yield node
        for _rel, child in self.get_children(node):
            for descendant in self.get_descendants(child, exclude):
                yield descendant
