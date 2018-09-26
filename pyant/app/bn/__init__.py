from pyant.app.bn import build, dashboard, patch

__all__ = ('bn_build', 'bn_dashboard', 'bn_patch', 'bn_installation')

class bn_build(build.build):
    pass

class bn_dashboard(dashboard.dashboard):
    pass

class bn_patch(patch.patch):
    pass

class bn_installation(patch.installation):
    pass
