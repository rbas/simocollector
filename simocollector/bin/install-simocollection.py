# -*- coding: utf-8 -*-
import os
import argparse
import json
import subprocess
import urllib2
import getpass
import socket

from simocollector.sender import BaseSender
from simocollector.collectors import system_info_collector
from simocollector.utils import slugify
from simocollector.sample_config import default_config


class ServerInfoSender(BaseSender):
    name = 'server'

    def __init__(self, config, ip, name):
        if 'server_id' not in config:
            config['server_id'] = ''
        super(ServerInfoSender, self).__init__(config)
        self.ip = ip
        self.server_name = slugify(unicode(name))

    def get_data(self):
        raw_data = system_info_collector.get_system_info()
        data = {
            'distribution': raw_data['distro'].get('distribution', 'unknown'),
            'release': raw_data['distro'].get('release', 'unknown'),
            'cpu_model_name': raw_data['processor'].get('model-name', 'unknown'),
            'cpu_number_of_cores': raw_data['processor'].get('cpu-cores', 0),
            'name': self.server_name,
            'slug': self.server_name,
            'ip_address': self.ip,
        }
        return data

    def _add_addtional_data(self, data):
        return data


def _get_hostname():
    return subprocess.Popen(['hostname'], stdout=subprocess.PIPE, close_fds=True).communicate()[0].strip()


def _get_host_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('google.com', 80))
    ip = s.getsockname()[0]
    s.close()

    return ip


def create_cron_jobs():
    publisher_path = subprocess.Popen(['which', 'simo-collection-publish.py'],
                                      stdout=subprocess.PIPE, close_fds=True).communicate()[0].strip()
    jobs = [
        '*/5 * * * * root {} -t loadavg'.format(publisher_path),
        '*/10 * * * * root {} -t cpu'.format(publisher_path),
        '*/15 * * * * root {} -t memory'.format(publisher_path),
    ]

    filename = '/etc/cron.d/simo-collector'

    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))

    with open(filename, 'w') as f:
        f.write('\n'.join(jobs))
        f.close()


def main():
    create_cron_jobs()
    parser = argparse.ArgumentParser(description='Create sample configuration of SIMO Collector')
    parser.add_argument('path', default='/etc/simo/collector.conf', type=str, nargs='?',
                        help='path to configuration file (default /etc/simo/collector.conf).')

    args = parser.parse_args()

    actual_user = getpass.getuser()
    host_ip_address = _get_host_ip_address()
    current_hostname = _get_hostname()

    username = raw_input('Username [{}]: '.format(actual_user)) or actual_user
    password = getpass.getpass('Password: ')
    server = raw_input('SIMO url: ')
    ip_address = raw_input('Write server ip address [{}]: '.format(host_ip_address)) or host_ip_address
    hostname = raw_input('Server name [{}]: '.format(current_hostname)) or current_hostname

    config = {
        'username': username,
        'password': password,
        'server': server
    }

    try:
        sender = ServerInfoSender(config, ip_address, hostname)
        response = sender.send()
        response_data = json.load(response)
    except urllib2.HTTPError, e:
        print(e.fp.read())
        exit(1)

    if 'id' not in response_data:
        print(response_data)
        exit(1)

    default_config['server_id'] = response_data['id']
    default_config['server'] = server
    default_config['username'] = username
    default_config['password'] = password

    config_path = args.path

    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path))

    with open(config_path, 'w') as f:
        f.write(json.dumps(default_config))

    print('Creating configuration on path {}'.format(config_path))

    create_cron_jobs()

if __name__ == '__main__':
    main()
