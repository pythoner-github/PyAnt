import re

__all__ = ('vars_expand',)

def vars_expand(string, opt = None):
    if opt is None:
        opt = {}

    m = re.search(r'\$(\(([\w.:-]+)\)|{([\w.:-]+)})', string)

    if m:
        val = m.group(1)[1:-1]

        if opt.get(val):
            str = opt[val]
        else:
            str = m.string[m.start():m.end()]

        return '%s%s%s' % (m.string[:m.start()], str, vars_expand(m.string[m.end():], opt))
    else:
        return string
