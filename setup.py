from distutils.core import setup

setup(
    name        = 'PyAnt',
    version     = '0.0.1',
    description = 'intelligent agent',
    author      = 'jack',
    packages    = ('pyant', 'pyant.app', 'pyant.builtin', 'pyant.app.bn', 'pyant.app.umebn')
)