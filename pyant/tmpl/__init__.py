import glob
import os.path
import shutil

from pyant.builtin import __os__

with __os__.chdir(os.path.dirname(__file__)) as chdir:
    for file in glob.iglob('*'):
        if file in ('__init__.py',):
            continue

        if os.path.isfile(file):
            name, extname = os.path.os.path.splitext(file)

            if extname in ('.py',):
                if not os.path.isfile(name):
                    try:
                        shutil.copyfile(file, name)
                    except:
                        pass


# TMPL

TMPL_CHANGES = os.path.abspath(os.path.join(os.path.dirname(__file__), 'changes.xltm'))
