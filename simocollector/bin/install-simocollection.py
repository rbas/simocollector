#!/usr/bin/env python
import os
import argparse
import json
import subprocess
import urllib2
import getpass
import socket

from simocollector.sender import BaseObjectSender, BaseMultiObjectSender
from simocollector.collectors import system_info_collector
from simocollector.utils import slugify
from simocollector.sample_config import default_config


CRON_JOB_FILENAME = '/etc/cron.d/simo-collector'
CONFIG_FILE_DEFAULT_PATH = '/etc/simo/collector.conf'


class ServerInfoSender(BaseObjectSender):
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

    def add_additional_data(self, data):
        return data


class DiskRegisterSender(BaseMultiObjectSender):
    name = 'disk'

    def get_data(self):
        raw_data = system_info_collector.get_disk_usage()
        data = []
        for partition_name, partition_data in raw_data.iteritems():
            disk_data = {
                'partition_name': partition_name,
                'path': partition_data['path'],
                'total': partition_data['total'],
                'volume': partition_data['volume']
            }
            data.append(self.add_additional_data(disk_data))

        return data


class NetDeviceRegisterSender(BaseMultiObjectSender):
    name = 'netdevice'

    def get_data(self):
        raw_data = system_info_collector.get_network_traffic()
        data = []
        for device_name in raw_data.iterkeys():
            device_data = {
                'name': device_name,
            }
            data.append(self.add_additional_data(device_data))

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
        '*/2 * * * * root {0} -t loadavg'.format(publisher_path),
        '*/6 * * * * root {0} -t networktraffic'.format(publisher_path),
        '*/5 * * * * root {0} -t cpu'.format(publisher_path),
        '*/9 * * * * root {0} -t memory'.format(publisher_path),
        '1 */3 * * * root {0} -t diskusage'.format(publisher_path),
        '1 3 * * * root {0} -t diskio'.format(publisher_path),
    ]

    if not os.path.exists(os.path.dirname(CRON_JOB_FILENAME)):
        os.makedirs(os.path.dirname(CRON_JOB_FILENAME))

    with open(CRON_JOB_FILENAME, 'w') as f:
        f.write('{0}\n\n'.format('\n'.join(jobs)))
        f.close()


def _wrap_with(code):
    def inner(text, bold=False):
        c = code
        if bold:
            c = "1;%s" % c
        return "\033[%sm%s\033[0m" % (c, text)

    return inner


red = _wrap_with('31')
green = _wrap_with('32')
yellow = _wrap_with('33')
blue = _wrap_with('34')
magenta = _wrap_with('35')
cyan = _wrap_with('36')
white = _wrap_with('37')


def main():
    parser = argparse.ArgumentParser(description='SIMO Collector installer.')
    parser.add_argument('path', default=CONFIG_FILE_DEFAULT_PATH, type=str, nargs='?',
                        help='path to configuration file (default {0}).'.format(CONFIG_FILE_DEFAULT_PATH))

    args = parser.parse_args()

    actual_user = getpass.getuser()
    host_ip_address = _get_host_ip_address()
    current_hostname = _get_hostname()

    username = raw_input('Username [{0}]: '.format(actual_user)) or actual_user
    password = getpass.getpass('Password: ')
    server = raw_input('SIMO url: ')
    ip_address = raw_input('Write server ip address [{0}]: '.format(host_ip_address)) or host_ip_address
    hostname = raw_input('Server name [{0}]: '.format(current_hostname)) or current_hostname

    config = {
        'username': username,
        'password': password,
        'server': server
    }

    print('\n\n')

    try:
        sender = ServerInfoSender(config, ip_address, hostname)
        response = sender.send()
        response_data = json.loads(response)
    except urllib2.HTTPError, e:
        print(e.fp.read())
        exit(1)

    if 'url' not in response_data:
        print(red('Bad data response:'))
        print(response_data)
        exit(1)

    default_config['server_id'] = response_data['url']
    default_config['server'] = server
    default_config['username'] = username
    default_config['password'] = password

    config_path = args.path

    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path))

    try:
        response = DiskRegisterSender(default_config).send()
    except urllib2.HTTPError, e:
        print(red('Problem in disk registration process'))
        print(e.fp.read())
        exit(1)

    default_config['disk'] = {}
    for data in response:
        disk = json.loads(data)
        partition_name = disk['partition_name']
        print('{0}: {1}'.format(green('Disk partition has been registred'), partition_name))
        default_config['disk'][partition_name] = disk['url']

    try:
        response = NetDeviceRegisterSender(default_config).send()
    except urllib2.HTTPError, e:
        print(red('Problem in disk registration process'))
        print(e.fp.read())
        exit(1)

    default_config['networkdevices'] = {}
    for data in response:
        device_data = json.loads(data)
        device_name = device_data['name']
        print('{0}: {1}'.format(green('Network device has been registred'), device_name))
        default_config['networkdevices'][device_name] = device_data['url']

    with open(config_path, 'w') as f:
        f.write(json.dumps(default_config, indent=4, sort_keys=True))

    print('{0}: {1}'.format(green('Creating configuration on path'), config_path))

    print('{0}: {1}'.format(green('Creating cron jobs'), CRON_JOB_FILENAME))
    create_cron_jobs()

    print('\n\n{0}'.format(green('Successfully installed SIMO Collector')))


def mmain():
    conf = '/home/rbas/simocollector.conf'
    with open(conf, 'r') as f:
        default_config = json.load(f)

    try:
        response = NetDeviceRegisterSender(default_config).send()
    except urllib2.HTTPError, e:
        print(e.fp.read())
        exit(1)

    default_config['networkdevices'] = {}
    for data in response:
        device_data = json.loads(data)
        default_config['networkdevices'][device_data['name']] = device_data['url']

    json_config = json.dumps(default_config, indent=4, sort_keys=True)
    with open(conf, 'w') as f:
        f.write(json_config)


if __name__ == '__main__':
    main()
