# -*- coding: utf-8 -*-
__all__ = ['ALLOWED_SEND_METHOD', 'build_sender', 'BaseSender', 'MemorySender', 'LoadaAvgSender', 'CPUSender']

import urllib2
import json
import datetime
import base64

from simocollector.collectors import system_info_collector


ALLOWED_SEND_METHOD = ('loadavg', 'cpu', 'memory', 'diskusage', 'diskio', 'networktraffic')

URL_LIST = {
    'memory': '/api/memory/',
    'loadavg': '/api/load-avg/',
    'cpu': '/api/cpu-utilization/',
    'server': '/api/server/',
    'disk': '/api/disk/',
    'diskusage': '/api/disk-usage/',
    'diskio': '/api/disk-io/',
    'netdevice': '/api/network-device/',
    'networktraffic': '/api/network-traffic/',
}


class SenderMixin(object):

    def send_data(self, url, data):
        base64string = base64.encodestring(
            '{0}:{1}'.format(self.get_username(), self.get_password())).replace('\n', '')

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SIMO Collector {0}'.format(__import__('simocollector').__versionstr__),
            'Authorization': "Basic {0}".format(base64string)
        }
        request = urllib2.Request(url, None, headers=headers)

        response = urllib2.urlopen(request, data=data)

        return response

    def get_username(self):
        return ''

    def get_password(self):
        return ''


class BaseSender(SenderMixin):

    name = ''

    def __init__(self, config):
        self.validate_config(config)
        self.config = config

    def get_url(self):
        try:
            return '{0}{1}'.format(self.config['server'].rstrip('/'), URL_LIST[self.name])
        except KeyError:
            raise Exception('Collection {0} is not allowed.'.format(self.name))

    def get_data(self):
        return {}

    def get_username(self):
        return self.config['username']

    def get_password(self):
        return self.config['password']

    def add_additional_data(self, data):
        data['created'] = datetime.datetime.now().isoformat()

        data['server'] = self.config['server_id']
        return data

    def validate_config(self, config):
        for reqire_argument in self.get_required_config_params():
            if not reqire_argument in config:
                raise Exception('Missing parameter "{0}" in configuration file.'.format(reqire_argument))

        return True

    def get_required_config_params(self):
        return 'server', 'server_id', 'username', 'password'


class BaseObjectSender(BaseSender):

    def send(self):
        data = self.add_additional_data(self.get_data())
        return self.send_data(self.get_url(), json.dumps(data)).read()


class BaseMultiObjectSender(BaseSender):

    def send(self):
        data = self.get_data()
        url = self.get_url()
        result = [self.send_data(url, json.dumps(item)).read() for item in data]
        return result


class MemorySender(BaseObjectSender):
    name = 'memory'

    def get_data(self):
        return system_info_collector.get_memory_info()


class LoadaAvgSender(BaseObjectSender):
    name = 'loadavg'

    def get_data(self):
        data = system_info_collector.get_load_average()

        return data


class CPUSender(BaseObjectSender):
    name = 'cpu'

    def get_data(self):
        return system_info_collector.get_cpu_utilization()


class DiskUsageSender(BaseMultiObjectSender):
    name = 'diskusage'

    def get_data(self):
        path_list = self.config['path_list']
        data = system_info_collector.get_disk_usage(path_list)
        result = []
        for partition_name, partition_data in data.iteritems():
            if partition_name in self.config['disk']:
                row = {
                    'used': partition_data['used'],
                    'free': partition_data['free'],
                    'percent': partition_data['percent'],
                    'disk': self.config['disk'][partition_name]
                }
                result.append(self.add_additional_data(row))
        return result

    def get_required_config_params(self):
        params = super(DiskUsageSender, self).get_required_config_params()
        params += ('disk', 'path_list')
        return params


class DiskIOSender(BaseMultiObjectSender):
    name = 'diskio'

    def get_data(self):
        data = system_info_collector.get_disk_io()
        result = []
        for partition_name, partition_data in data.iteritems():
            if partition_name in self.config['disk']:
                row = partition_data
                row['disk'] = self.config['disk'][partition_name]
                result.append(self.add_additional_data(row))

        return result

    def get_required_config_params(self):
        params = super(DiskIOSender, self).get_required_config_params()
        params += ('disk', )
        return params


class NetworkTrafficSender(BaseMultiObjectSender):
    name = 'networktraffic'

    def get_data(self):
        raw_data = system_info_collector.get_network_traffic()
        result = []
        for device_name, device_data in raw_data.iteritems():
            if device_name in self.config['networkdevices']:
                row = {
                    'received': device_data['kb_received'],
                    'transmitted': device_data['kb_transmitted'],
                    'device': self.config['networkdevices'][device_name]
                }
                result.append(self.add_additional_data(row))

        return result

    def get_device_id(self, device_name):
        try:
            return self.config['networkdevices'][device_name]
        except KeyError:
            raise Exception('Network device {0} is not registred.'.format(device_name))

    def get_required_config_params(self):
        params = super(NetworkTrafficSender, self).get_required_config_params()
        params += ('networkdevices', )
        return params


def build_sender(name, config):
    return {
        'cpu': CPUSender(config),
        'loadavg': LoadaAvgSender(config),
        'memory': MemorySender(config),
        'diskusage': DiskUsageSender(config),
        'diskio': DiskIOSender(config),
        'networktraffic': NetworkTrafficSender(config)
    }[name]
