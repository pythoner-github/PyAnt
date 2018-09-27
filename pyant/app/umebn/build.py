from pyant.app import __build__

__all__ = ('build', )

class build(__build__):
    def __init__(self):
        artifact_repos = {
            'snapshot'  : 'umebn-snapshot-generic',
            'alpha'     : 'umebn-alpha-generic',
            'release'   : 'umebn-release-generic'
        }

        super().__init__(
            'umebn',
            __os__.join(const.SSH_GIT, 'umebn'),
            artifact_repos
        )

        self.type = 'umebn'

    def update(self, branch = None):
        if os.path.isdir(self.path):
            if os.path.isfile(os.path.join(self.path, '.git/index.lock')):
                time.sleep(30)

                return True
            else:
                return git.pull(self.path, revert = True)
        else:
            return git.clone(self.repos, self.path, branch)

    def compile_pom(self, cmd = None):
        return super().compile_pom(cmd, 'devops/parent/build/pom.xml')

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        return const.METRIC_ID_UMEBN
