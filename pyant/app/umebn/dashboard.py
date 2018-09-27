from pyant.app import __dashboard__

from pyant.app.umebn import build

__all__ = ('dashboard', )

class dashboard(__dashboard__):
    def __init__(self):
        super().__init__('umebn', build.build().repos)

    # ------------------------------------------------------

    def update(self, branch = None):
        return build.build().update(branch)
