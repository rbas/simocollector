#!/bin/bash
# Author: Martin Voldrich <rbas.cz@gmail.com>
VERSION='1.2.3'

command_exists() {
    type "$1" &> /dev/null ;
}

install_simo_collector() {

    # Install depencies
    if dpkg-query -s curl gcc python-dev >> /dev/null ; then
        echo "***Requirements already installed"
    else
        echo "** Installing requirements"
        apt-get -y install curl gcc python-dev
    fi

    if dpkg-query -W curl gcc python-dev; then
        echo "** Requirements successfuly installed!"
    fi

    # Install easy_install if necessary
    if ! command_exists easy_install ; then
        curl -O "https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py"
        /usr/bin/env python ez_setup.py
        rm -f ez_setup.py
    fi

    # Install argparse and psutil if necessary
    easy_install argparse
    easy_install psutil


    echo "Download SIMO collector..."
    curl -O https://pypi.python.org/packages/source/s/simocollector/simocollector-${VERSION}.tar.gz

    tar xfz simocollector-${VERSION}.tar.gz

    cd simocollector-${VERSION}
    /usr/bin/env python setup.py install

    /usr/bin/env python $(which install-simocollection.py)
}

install_simo_collector
