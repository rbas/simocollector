#!/usr/bin/env python
import sys
import json
import argparse

from simocollector.sample_config import default_config


def main():
    parser = argparse.ArgumentParser(description='Create sample configuration of SIMO Collector')
    parser.add_argument('path', default='/etc/simo/collector.conf', type=str, nargs='?',
                        help='path to configuration file (default /etc/simo/collector.conf).')

    if not len(sys.argv) > 1:
        parser.print_usage()
        exit(0)

    args = parser.parse_args()

    with open(args.path, 'w') as f:
        f.write(json.dumps(default_config))

    print('Creating sample configuration on path {0}'.format(args.path))


if __name__ == '__main__':
    main()