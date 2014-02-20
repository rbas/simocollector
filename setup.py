from setuptools import setup

setup(
    name='simocollector',
    version='1.0.0',
    packages=['simocollector'],
    url='https://github.com/rbas/simocollector',
    license='MIT',
    author='rbas',
    author_email='rbas.cz@gmail.com',
    description='SIMO Collector',
    scripts=['simocollector/bin/simo-collection-publish.py',
             'simocollector/bin/create-simo-config.py',
             'simocollector/bin/install-simocollection.py'],
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet',
    )
)
