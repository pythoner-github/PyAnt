import os
import os.path

from pyant import command, maven
from pyant.app import const, __build__
from pyant.builtin import __os__

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
            const.UMEBN_REPOS,
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

    def compile(self, cmd = None, clean = False, retry_cmd = None, dirname = None):
        if not dirname:
            dirname = 'build'

        if not super().compile(cmd, clean, retry_cmd, dirname):
            return False

        with __os__.chdir(self.path) as chdir:
            mvn = maven.maven()
            map = mvn.artifactid_paths(dirname)

            for path in map.values():
                if not self.oki(path, os.environ.get('VERSION')):
                    return False

        return True

    # ------------------------------------------------------

    def metric_id(self, module_name = None):
        return const.METRIC_ID_UMEBN

    def oki(self, path, version):
        if os.path.isdir(os.path.join(path, 'output')):
            cmd = command.command()
            cmdline = 'python3 %s %s %s' % (const.OKI_FILE, os.path.join(path, 'output'), version)

            for line in cmd.command(cmdline):
                print(line)

        return True
