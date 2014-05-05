import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages  # NOQA

base_path = os.path.dirname(__file__)


def read_file(filename):
    return open(os.path.join(base_path, filename)).read()

setup(
    name='simocollector',
    version='1.3.0',
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
