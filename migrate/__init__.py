from flask import g


def MSG(txt):
    if not hasattr(g, 'msg'):
        g.msg = []
    print(txt)
    g.msg += [txt]
