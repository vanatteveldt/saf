import collections

class SAF(object):
    def __init__(self, saf):
        self.saf = saf
        self._tokens = {t['id']: t for t in saf['tokens']}
        self._children = None # cache token : [(rel, child), ...]

    def get_token(self, token_id):
        return self._tokens[token_id]

    def get_parent(self, token):
        self._cache_children()
        for parent, children in self._children.iteritems():
            for rel, child in children:
                if child == token:
                    return rel, self.get_token(parent)
        return None, None
        

    def _cache_children(self):
        if self._children is None:
            self._children = collections.defaultdict(list)
            for rel in self.saf['dependencies']:
                self._children[rel['parent']].append((rel['relation'], self.get_token(rel['child'])))
            
    def get_children(self, token):
        if not isinstance(token, int): token = token['id']
        self._cache_children()
        return self._children[token]

    def get_child(saf, token, *rels, **criteria):
        def _get_seq(v):
            return v if isinstance(v, (list, tuple, set)) else [v]
        for rel, child in saf.get_children(token):
            if (not rels) or rel in rels:
                if all(child[k] in _get_seq(v) for (k,v) in criteria.iteritems()):
                    return child
        
    def __getattr__(self, attr):
        if attr != "saf" and not attr.startswith("_"):
            try:
                return self.saf[attr]
            except KeyError:
                pass
        return object.__getattribute__(self, attr)

    def __setattr__(self, attr, val):
        if attr == "saf" or attr.startswith("_"):
            return super(SAF, self).__setattr__(attr, val)
        else:
            self.saf[attr] = val
        
            
    def get_tokens(self, sentence=None):
        """Return the tokens in this article or sentence ordered by sentence and offset"""
        tokens = self.saf['tokens']
        if sentence is not None:
            tokens = [t for t in tokens if t['sentence'] == sentence]
        return sorted(tokens, key = lambda t: (int(t['sentence']), int(t['offset'])))

    def resolve(self, ids=None):
        """
        Resolve the given token ids (or the whole article) to dictionaries
        Will contain token information (lemma, pos) and additional information
        such as codes, coreference, etc. if available
        """
        # get token dicts for given ids (or whole article)
        if ids is not None:
            tokens = (self.get_token(id) for id in ids)
        else:
            tokens = self.tokens
        tokens = sorted(tokens, key = lambda t: (int(t['sentence']), int(t['offset'])))

        # get entities (if available)
        if 'entities' in self.saf:
            for entity in self.entities:
                for token in entity['tokens']:
                    self.get_token(token)['entity'] = entity['type']
        
        # get coreferences (if available)
        if 'coreferences' in self.saf:
            corefs = dict(self.get_coreferences())
            coref_groups = {group: i+1 for (i, group) in enumerate(map(tuple, corefs.values()))}
            for token in tokens:
                if token['id'] in corefs:
                    token['coref'] = coref_groups[tuple(corefs[token['id']])]

        # get codes (if available)
        if 'codes' in self.saf:
            for code in self.codes:
                token = self.get_token(code['token'])
                token['codes'] = tuple(set(token.get('codes', ()) + (code['code'],)))

        # add sources (if available)
        if 'sources' in self.saf:
            src_roles = {} # source role per token
            for i, source in enumerate(self.sources):
                for place in "source", "quote":
                    for token in source[place]:
                        src_roles[token] = (place, i)
            for token in tokens:
                if token['id'] in src_roles:
                    token['source_role'], token['source_id'] = src_roles[token['id']]

        # add clauses (if available)
        if 'clauses' in self.saf:
            roles = {} # role per token
            for i, clause in enumerate(self.get_reduced_clauses()):
                for place in "subject", "predicate":
                    for token in clause[place]:
                        roles[token] = (place, i)
            for token in tokens:
                if token['id'] in roles:
                    token['clause_role'], token['clause_id'] = roles[token['id']]


        return tokens

    def resolve_passive(self):
        remove = set()
        add = []
        for tok in self.tokens:
            if tok['lemma'] in ('word', 'ben'): # possible passive
                verb = self.get_child(tok, "vc")
                if not verb: continue
                door = self.get_child(verb, "mod", lemma="door")
                if not door: continue
                if len(self.get_children(door)) != 1: continue
                agent = self.get_child(door, "obj1")
                if not agent: continue
                # passive! remove tok and door, add verb - agent
                remove |= {tok['id'], door['id']}
                add += [{"relation": "agent", "parent": verb['id'], "child": agent['id']}]
                for rel, child in self.get_children(tok):
                    if rel not in ["su", "vc"]:
                        add += [{"relation": rel, "parent": verb['id'], "child": child["id"]}]

        if remove:
            result = SAF(self.saf.copy())
            result.tokens = [t for t in self.tokens if t['id'] not in remove]
            deps = [dep for dep in self.dependencies
                    if dep['parent'] not in remove
                    and dep['child'] not in remove]
            deps += add
            result.dependencies = deps
            return result
        return self

        
    def get_source(self, tokenids):
        "Return the source tokens (if any) of a source that contains all tokens"
        for source in self.sources:
            if set(tokenids).issubset(set(source['quote'])):
                for token in source['source']:
                    yield token


    def get_reduced_clauses(self):
        "Reduce the clauses in saf by removing nested clauses and adding the source"
        def contained_tokens(predicate):
            for clause in self.clauses:
                p2 = set(clause['predicate']) | set(clause['subject'])
                if p2 != set(predicate) and p2.issubset(predicate):
                    for t in p2:
                        yield t
            for source in self.sources:
                # exclude sources from predicates
                if set(source['source']).issubset(set(predicate)):
                    for t in source['source']:
                        yield t
        for clause in self.clauses:
            clause = clause.copy()
            contained = set(contained_tokens(clause['predicate']))
            clause['predicate'] = [t for t in clause['predicate'] if t not in contained]
            if 'sources' in self.saf:
                clause['source'] = list(set(self.get_source(clause['predicate'])))

            yield clause


    def get_roots(self, sentence):
        parents = {d['child'] : d['parent'] for d in self.saf['dependencies']
                   if self.get_token(d['child'])['sentence'] == sentence}
        # root is a parent that has no parents
        return (self.get_token(root) for root in parents.values()
                if root not in set(parents.keys()))
        
            
    def get_root(self, sentence):
        roots = list(self.get_roots(sentence))
        if len(roots) != 1:
            raise ValueError("Sentence {sentence} has roots {roots}".format(**locals()))
        return roots[0]

    def get_sentences(self):
        return sorted({t['sentence'] for t in self.saf['tokens']})

    def get_node_depths(self, sentence):
        # return a dict with the dept of each node
        rels = [d for d in self.saf['dependencies']
            if self.get_token(d['child'])['sentence'] == sentence]
        generations = {node['id']: 0 for node in self.get_roots(sentence)}
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

    def is_descendant(self, node, possible_ancestor):
        return any(node == descendant['id'] for descendant in self.get_descendants(possible_ancestor))


    def get_coreferences(self):
        """Decode the SAF coreferences as (node: coreferencing_nodes) pairs"""

        def _merge(lists):
            """
            Merge the lists so lists with overlap are joined together
            (i.e. [[1,2], [3,4], [2,5]] --> [[1,2,5], [3,4]])
            from: http://stackoverflow.com/a/9400562
            """
            newsets, sets = [set(lst) for lst in lists if lst], []
            while len(sets) != len(newsets):
                sets, newsets = newsets, []
                for aset in sets:
                    for eachset in newsets:
                        if not aset.isdisjoint(eachset):
                            eachset.update(aset)
                            break
                    else:
                        newsets.append(aset)
            return newsets

        coref_groups = []
        for coref in self.saf.get('coreferences', []):
            nodes = []
            for place in coref:
                nodes += place
            coref_groups.append(nodes)
        for nodes in _merge(coref_groups):
            for node in nodes:
                yield node, nodes
