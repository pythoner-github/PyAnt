import re

__all__ = ('vars_expand',)

def vars_expand(string, vars = None):
    if vars is None:
        vars = {}

    m = re.search(r'\$(\(([\w.:-]+)\)|{([\w.:-]+)})', string)

    if m:
        val = m.group(1)[1:-1]

        if vars.get(val):
            str = vars[val]
        else:
            str = m.string[m.start():m.end()]

        return '%s%s%s' % (m.string[:m.start()], str, vars_expand(m.string[m.end():], vars))
    else:
        return string
