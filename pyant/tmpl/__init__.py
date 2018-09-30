import glob
import os.path
import shutil

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

