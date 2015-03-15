from pygraphviz import AGraph
import itertools
import base64

def get_png_bytes(saf, **options):
    g = get_graphviz(saf, **options)
    return base64.b64encode(g.draw(format='png', prog='dot'))

def get_graphviz(saf):
    """
    Create a pygraphviz graph from the SAF dependencies
    """
    g = AGraph(directed=True, strict=False)
    nodeset = set(itertools.chain.from_iterable((t['child'], t['parent'])
                                      for t in saf.saf['dependencies']))
    for n in sorted(nodeset):
        g.add_node(n, **node_hook(saf, n))
    connected = set()
    # create edges
    for triple in saf.saf['dependencies']:
        kargs = triple_hook(saf, triple)
        g.add_edge(triple['child'], triple['parent'], **kargs)
    # some theme options
    for obj, attrs in THEME.iteritems():
        for k, v in attrs.iteritems():
            getattr(g, "%s_attr" % obj)[k] = v
    return g


    
def node_hook(saf, token_id):
    token = saf.get_token(token_id)
    label = token['word']
    labels = ["%s: %s" % (token['id'], token['word'])]
    labels += ["%s / %s" % (token['lemma'], token['pos1'])]
    #labels += ["%s: %s" % (k, v)
    #           for k, v in token.__dict__.iteritems()
    #           if k not in VIS_IGNORE_PROPERTIES]
    return {"label": "\\n".join(labels)}

def triple_hook(saf, triple):
    kargs = {'label': triple['relation']}
    return kargs

THEME = {"graph" : {"rankdir" : "BT",
                                "concentrate" : "false"},
                     "node" : {"shape" : "rect",
                               "fontsize" : 10},
                     "edge" : {"edgesize" : 10,
                               "fontsize" : 10}}
