import os
import subprocess
import re
import psutil
import platform


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
        distro = {}
        system_info = {}
        dist = platform.dist()
        if filter(None, dist):
            distro['distribution'] = dist[0]
            distro['release'] = '{0}/{1}'.format(dist[1], dist[2])
        else:
            distro['distribution'] = platform.system()
            distro['release'] = platform.release()

        system_info["distro"] = distro

        processor = {
            'cpu-cores': psutil.NUM_CPUS
        }

        try:
            if os.path.exists('/proc/cpuinfo'):
                model_name_raw = subprocess.Popen(['grep', '"model name"', '-m', '1', '/proc/cpuinfo'],
                                                  stdout=subprocess.PIPE,
                                                  close_fds=True).communicate()[0]
                cpu_model_name = model_name_raw.replace('model name', '').strip().lstrip(':').strip()
            elif os.path.exists('/var/run/dmesg.boot'):
                model_name_raw = subprocess.Popen(['grep', 'CPU:', '/var/run/dmesg.boot'],
                                                  stdout=subprocess.PIPE,
                                                  close_fds=True).communicate()[0]
                cpu_model_name = model_name_raw.replace('CPU:', '').strip()
            else:
                cpu_model_name = 'unknown'
        except Exception:
            cpu_model_name = 'unknown'

        processor['model-name'] = cpu_model_name

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

    def get_disk_usage(self, path_list):
        _columns = ('total', 'used', 'free')
        data = {}

        partition_list = psutil.disk_partitions(all=True)

        def _sanitize(p):
            if p is not "/":
                return p.rstrip("/")
            return p
        path_list = map(_sanitize, path_list)

        for path in path_list:
            try:
                part = filter(lambda x: x.mountpoint == path, partition_list)[0]
                if os.name == 'nt':
                    if 'cdrom' in part.opts or part.fstype == '':
                        # skip cd-rom drives with no disk in it; they may raise
                        # ENOENT, pop-up a Windows GUI error for a non-ready
                        # partition or just hang.
                        continue
                usage = psutil.disk_usage(part.mountpoint)
                row = dict(zip(_columns, map(lambda x: x / (1024 * 1024), usage)))  # Convert to MB
                row['volume'] = part.device
                row['path'] = part.mountpoint
                row['percent'] = int(usage.percent)

                data[part.device.replace('/dev/', '')] = row
            except IndexError:
                pass

        return data

    def get_disk_io(self):
        raw_data = psutil.disk_io_counters(True)
        data = {}
        for disk_name, disk_data in raw_data.iteritems():
            row_data = dict(disk_data._asdict())
            row_data['read_kb'] = row_data['read_bytes'] / 1024  # Convert to KB
            row_data['write_kb'] = row_data['write_bytes'] / 1024  # Convert to KB
            del(row_data['read_bytes'])
            del(row_data['write_bytes'])

            data[disk_name] = row_data

        return data

    def get_network_traffic(self):
        data = {}
        for device, stat in psutil.net_io_counters(pernic=True).iteritems():
            data[device] = {'kb_received': stat.bytes_recv / 1024, 'kb_transmitted': stat.bytes_sent / 1024}

        return data

    def get_load_average(self):
        _loadavg_columns = ('minute', 'five_minutes', 'fifteen_minutes')
        load_dict = dict(zip(_loadavg_columns, os.getloadavg()))

        cores = psutil.NUM_CPUS
        load_dict['cores'] = cores

        return load_dict

    def get_cpu_utilization(self):
        _columns = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'quest', 'quest_nice')
        cpu_time_percent = psutil.cpu_times_percent(interval=3)
        data = dict(zip(_columns, cpu_time_percent))
        return data

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
