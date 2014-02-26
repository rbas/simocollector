#!/usr/bin/env python
import sys
import os
import argparse
import json
from urllib2 import HTTPError

from simocollector.sender import ALLOWED_SEND_METHOD, build_sender


def parse_config_file(path):
    with open(path, 'r') as f:
        data = json.load(f)

    return data


def main():
    str_bool_values = ('y', 'yes', 'true', 't', '1')

    def str2bool(v):
        return v.lower() in str_bool_values

    parser = argparse.ArgumentParser(description='SIMO collector')
    parser.add_argument('-t', '--type', choices=ALLOWED_SEND_METHOD, type=str, required=True,
                        help='type of collection')

    parser.add_argument('-c', '--config', default='/etc/simo/collector.conf', type=str,
                        help='path to configuration file (default /etc/simo/collector.conf).')

    parser.add_argument('-o', '--output', default=False, type=bool,
                        help='render output? ({0})'.format(', '.join(str_bool_values)))
    parser.register('type', 'bool', str2bool)

    if not len(sys.argv) > 1:
        parser.print_usage()
        exit(0)

    args = parser.parse_args()

    def strip(text):
        if text:
            return text.strip('"').strip("'")

    config_path = strip(args.config)
    if not os.path.exists(config_path):
        print('Config file {0} does not exists.'.format(config_path))
        sys.exit(1)

    config = parse_config_file(config_path)
    try:
        response = build_sender(strip(args.type), config).send()
        if args.output:
            print(response)
    except HTTPError, e:
        if args.output:
            if hasattr(e, 'fp'):
                print(e.fp.read())
            else:
                raise e


if __name__ == '__main__':
    main()
