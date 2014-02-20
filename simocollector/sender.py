# -*- coding: utf-8 -*-
__all__ = ['ALLOWED_SEND_METHOD', 'build_sender', 'BaseSender', 'MemorySender', 'LoadaAvgSender', 'CPUSender']

import urllib2
import json
import datetime
import base64

from .collectors import system_info_collector


ALLOWED_SEND_METHOD = ('loadavg', 'cpu', 'memory')

URL_LIST = {
    'memory': '/api/memory/',
    'loadavg': '/api/load-avg/',
    'cpu': '/api/cpu-utilization/',
    'server': '/api/server/',
}


class BaseSender(object):

    name = ''

    def __init__(self, config):
        _required_arguments = ('server', 'server_id', 'username', 'password')

        for reqire_argument in _required_arguments:
            assert(reqire_argument in config)

        self.config = config

    def send(self):
        data = self._add_addtional_data(self.get_data())
        return self._send(self.get_url(), json.dumps(data))

    def get_url(self):
        try:
            return '{}{}'.format(self.config['server'].rstrip('/'), URL_LIST[self.name])
        except KeyError:
            raise Exception('Collection {} is not allowed.'.format(self.name))

    def get_data(self):
        return {}

    def _send(self, url, data):
        request = urllib2.Request(url, None, headers={'Content-Type': 'application/json'})

        base64string = base64.encodestring('%s:%s' % (self.config['username'], self.config['password'])).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)

        response = urllib2.urlopen(request, data=data)

        return response

    def _add_addtional_data(self, data):
        data['created'] = datetime.datetime.now().isoformat()

        data['server'] = self.config['server_id']
        return data


class MemorySender(BaseSender):
    name = 'memory'

    def get_data(self):
        return system_info_collector.get_memory_info()


class LoadaAvgSender(BaseSender):
    name = 'loadavg'

    def get_data(self):
        data = system_info_collector.get_load_average()
        data['processed_entities'], data['entities'] = data['scheduled_processes'].split('/')

        del(data['scheduled_processes'])

        return data


class CPUSender(BaseSender):
    name = 'cpu'

    def get_data(self):
        return system_info_collector.get_cpu_utilization()


def build_sender(name, config):
    return {
        'cpu': CPUSender(config),
        'loadavg': LoadaAvgSender(config),
        'memory': MemorySender(config)
    }[name]


def main():
    try:
        config = json.load(open('/home/rbas/simocollector.conf'))

        print(build_sender('cpu', config).send().read())
    except urllib2.HTTPError, e:
        print(e.fp.read())


if __name__ == '__main__':
    main()
