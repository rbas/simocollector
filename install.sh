#!/bin/bash
# Author: Martin Voldrich <rbas.cz@gmail.com>
VERSION='1.1.0'

command_exists() {
    type "$1" &> /dev/null ;
}

install_simo_collector() {

    # Install depencies
    if dpkg-query -s curl sysstat >> /dev/null ; then
        echo "***Requirements already installed"
    else
        echo "** Installing requirements"
        apt-get -y install sysstat curl
    fi

    if dpkg-query -W sysstat curl; then
        echo "** Requirements successfuly installed!"
    fi

    # Install easy_install if necessary
    if ! command_exists easy_install ; then
        curl -O "https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py"
        /usr/bin/env python ez_setup.py
        rm -f ez_setup.py
    fi



    echo "Download SIMO collector..."
    curl -O https://pypi.python.org/packages/source/s/simocollector/simocollector-${VERSION}.tar.gz

    tar xfz simocollector-${VERSION}.tar.gz

    easy_install argparse

    cd simocollector-${VERSION}
    /usr/bin/env python setup.py install

    /usr/bin/env python $(which install-simocollection.py)
}

install_simo_collector
