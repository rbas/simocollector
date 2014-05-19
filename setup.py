import os
import sys
import shlex
import subprocess

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages  # NOQA

base_path = os.path.dirname(__file__)

version = __import__('simocollector').__versionstr__

# release a version, publish to GitHub and PyPI
if sys.argv[-1] == 'publish':
    command = lambda cmd: subprocess.check_call(shlex.split(cmd))
    command('git tag v' + version)
    command('git push --tags origin master:master')
    command('python setup.py sdist upload')
    sys.exit()


def read_file(filename):
    return open(os.path.join(base_path, filename)).read()

setup(
    name='simocollector',
    version=version,
    packages=find_packages(),
    url='https://github.com/rbas/simocollector',
    license=read_file('LICENSE'),
    author='Martin Voldrich',
    author_email='rbas.cz@gmail.com',
    description='SIMO Collector',
    long_description=read_file('README.rst'),
    scripts=['simocollector/bin/simo-collection-publish.py',
             'simocollector/bin/create-simo-config.py',
             'simocollector/bin/install-simocollection.py'],
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Monitoring',
    ),
    install_requires=['psutil', 'argparse']
)
