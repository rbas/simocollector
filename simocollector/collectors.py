import os
import sys
import subprocess
import re
import glob
import psutil

from .utils import split_and_slugify

try:
    from multiprocessing import cpu_count
except ImportError:
    def cpu_count():
        """ Returns the number of CPUs in the system
        """
        num = 1
        if sys.platform == 'win32':
            # fetch the cpu count for windows systems
            try:
                num = int(os.environ['NUMBER_OF_PROCESSORS'])
            except (ValueError, KeyError):
                pass
        elif sys.platform == 'darwin':
            # fetch teh cpu count for MacOS X systems
            try:
                num = int(os.popen('sysctl -n hw.ncpu').read())
            except ValueError:
                pass
        else:
            # an finally fetch the cpu count for Unix-like systems
            try:
                num = os.sysconf('SC_NPROCESSORS_ONLN')
            except (ValueError, OSError, AttributeError):
                pass

        return num


class SystemCollector(object):
    def get_uptime(self):

        with open('/proc/uptime', 'r') as line:
            contents = line.read().split()

        total_seconds = float(contents[0])

        MINUTE = 60
        HOUR = MINUTE * 60
        DAY = HOUR * 24

        days = int(total_seconds / DAY)
        hours = int((total_seconds % DAY) / HOUR)
        minutes = int((total_seconds % HOUR) / MINUTE)
        seconds = int(total_seconds % MINUTE)

        uptime = "{0} days {1} hours {2} minutes {3} seconds".format(days, hours, minutes, seconds)

        return uptime

    def get_system_info(self):
        distro_info_file = glob.glob('/etc/*-release')
        debian_version = glob.glob('/etc/debian_version')

        try:
            distro_info = subprocess.Popen(["cat"] + debian_version,
                                           stdout=subprocess.PIPE,
                                           close_fds=True).communicate()[0]
            debian = True
        except:
            distro_info = subprocess.Popen(["cat"] + distro_info_file,
                                           stdout=subprocess.PIPE,
                                           close_fds=True).communicate()[0]
            debian = False

        system_info = {}
        distro = {}
        if debian is False:
            for line in distro_info.splitlines():
                if re.search('distrib_id', line, re.IGNORECASE):
                    info = line.split("=")
                    if len(info) == 2:
                        distro['distribution'] = info[1]
                if re.search('distrib_release', line, re.IGNORECASE):
                    info = line.split("=")
                    if len(info) == 2:
                        distro['release'] = info[1]
        else:
            distro['distribution'] = 'Debian'
            distro['release'] = distro_info

        system_info["distro"] = distro

        processor_info = subprocess.Popen(["cat", '/proc/cpuinfo'],
                                          stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]

        processor = {}
        for line in processor_info.splitlines():
            parsed_line = split_and_slugify(line)
            if parsed_line and isinstance(parsed_line, dict):
                key = parsed_line.keys()[0]
                value = parsed_line.values()[0]
                processor[key] = value

        system_info["processor"] = processor

        return system_info

    def get_memory_info(self):
        _swap_columns = ('swap_total', 'swap_used', 'swap_free', 'swap_percent_used')
        swap_values = dict(zip(_swap_columns, psutil.swap_memory()))
        memory_usage = psutil.virtual_memory()

        raw_data = {
            "total": memory_usage.total,
            "free": memory_usage.free,
            "used": memory_usage.used,
            "percent_used": int(memory_usage.percent)
        }

        raw_data.update(swap_values)

        data = {}
        for name, value in raw_data.iteritems():
            value = int(value)
            if name.find('percent') is -1:
                value /= 1024 * 1024  # Convert to MB

            data[name] = value

        return data

    def get_disk_usage(self):
        df = subprocess.Popen(['df'], stdout=subprocess.PIPE, close_fds=True).communicate()[0]

        volumes = df.split('\n')
        volumes.pop(0)  # remove the header
        volumes.pop()

        data = {}

        _columns = ('volume', 'total', 'used', 'free', 'percent', 'path')

        previous_line = None

        for volume in volumes:
            line = volume.split(None, 6)

            if len(line) == 1:  # If the length is 1 then this just has the mount name
                previous_line = line[0]  # We store it, then continue the for
                continue

            if previous_line is not None:
                line.insert(0, previous_line)  # then we need to insert it into the volume
                previous_line = None  # reset the line

            if line[0].startswith('/'):
                _volume = dict(zip(_columns, line))

                _volume['percent'] = _volume['percent'].replace("%",
                                                                '')  # Delete the % sign for easier calculation later

                # strip /dev/
                _name = _volume['volume'].replace('/dev/', '')

                # Encrypted directories -> /home/something/.Private
                if '.' in _name:
                    _name = _name.replace('.', '')

                data[_name] = _volume

        return data

    def get_network_traffic(self):

        stats = subprocess.Popen(['sar', '-n', 'DEV', '1', '1'],
                                 stdout=subprocess.PIPE, close_fds=True) \
            .communicate()[0]
        network_data = stats.splitlines()
        data = {}
        for line in network_data:
            if line.startswith('Average'):
                elements = line.split()
                interface = elements[1]

                # interface name with .
                if '.' in interface:
                    interface = interface.replace('.', '-')

                if interface not in ['IFACE', 'lo']:
                    # rxkB/s - Total number of kilobytes received per second
                    # txkB/s - Total number of kilobytes transmitted per second

                    kb_received = elements[4].replace(',', '.')
                    kb_received = format(float(kb_received), ".2f")

                    kb_transmitted = elements[5].replace(',', '.')
                    kb_transmitted = format(float(kb_transmitted), ".2f")

                    data[interface] = {"kb_received": kb_received, "kb_transmitted": kb_transmitted}

        return data

    def get_load_average(self):
        _loadavg_columns = ('minute', 'five_minutes', 'fifteen_minutes')
        load_dict = dict(zip(_loadavg_columns, os.getloadavg()))

        cores = cpu_count()
        load_dict['cores'] = cores

        return load_dict

    def get_cpu_utilization(self):

        # Get the cpu stats
        mpstat = subprocess.Popen(['sar', '1', '1'],
                                  stdout=subprocess.PIPE, close_fds=True).communicate()[0]

        cpu_columns = []
        cpu_values = []
        header_regex = re.compile(r'.*?([%][a-zA-Z0-9]+)[\s+]?')  # the header values are %idle, %wait
        # International float numbers - could be 0.00 or 0,00
        value_regex = re.compile(r'\d+[\.,]\d+')
        stats = mpstat.split('\n')

        for value in stats:
            values = re.findall(value_regex, value)
            if len(values) > 4:
                values = map(lambda x: x.replace(',', '.'), values)  # Replace , with . if necessary
                cpu_values = map(lambda x: format(float(x), ".2f"),
                                 values)  # Convert the values to float with 2 points precision

            header = re.findall(header_regex, value)
            if len(header) > 4:
                cpu_columns = map(lambda x: x.replace('%', ''), header)

        cpu_dict = dict(zip(cpu_columns, cpu_values))

        return cpu_dict


system_info_collector = SystemCollector()


class ProcessInfoCollector(object):
    def __init__(self):
        memory = system_info_collector.get_memory_info()
        self.total_memory = memory['total']

    def process_list(self):
        stats = subprocess.Popen(['pidstat', '-ruht'],
                                 stdout=subprocess.PIPE, close_fds=True) \
            .communicate()[0]

        stats_data = stats.splitlines()
        del stats_data[0:2]  # Deletes Unix system data

        converted_data = []
        for line in stats_data:
            if re.search('command', line, re.IGNORECASE):  # Matches the first line
                header = line.split()
                del header[0]  # Deletes the # symbol
            else:
                command = line.split()
                data_dict = dict(zip(header, command))

                process_memory_mb = float(self.total_memory / 100) * float(
                    data_dict["%MEM"].replace(",", "."))  # Convert the % in MB
                memory = "{0:.3}".format(process_memory_mb)
                memory = memory.replace(",", ".")

                cpu = "{0:.2f}".format(float(data_dict["%CPU"].replace(",", ".")))
                cpu = cpu.replace(",", ".")

                command = data_dict["Command"]

                if not re.search('_', command, re.IGNORECASE):
                    extracted_data = {"cpu:%": cpu,
                                      "memory:mb": memory,
                                      "command": command}
                    converted_data.append(extracted_data)

        return converted_data


process_info_collector = ProcessInfoCollector()
