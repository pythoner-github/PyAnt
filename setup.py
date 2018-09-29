from distutils.core import setup

setup(
    name        = 'PyAnt',
    version     = '0.0.1',
    description = 'intelligent agent',
    author      = 'jack',
    author_email= '10067748@zte.com.cn',
    packages    = ('pyant', 'pyant.app', 'pyant.builtin', 'pyant.app.bn', 'pyant.app.umebn'),
    data_files  = [('tmpl/pyant', ['tmpl/changes.xltm', 'tmpl/template(U31R22).xml', 'tmpl/template(umebn).xml'])]
)