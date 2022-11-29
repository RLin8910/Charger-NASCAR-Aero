import shutil
import os
import sys

src = './template'
dst = './runtime'

if __name__ == '__main__':
    print(sys.argv)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
