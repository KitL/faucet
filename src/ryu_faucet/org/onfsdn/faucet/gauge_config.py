class GaugeConfig(object):

    defaults = {
        'gauge_type': None,
        'output_file': None,
        'interval': 30,
        'influx_stats': False,
        'influx_db': 'faucet',
        'influx_host': 'localhost',
        'influx_port': 8086,
        'influx_user': '',
        'influx_pwd': '',
        'influx_timeout': 10,
    }

    def __init__(self, conf):
        self.update(conf)
        self.set_defaults()

    def update(self, dictionary):
        self.__dict__.update(dictionary)

    def set_defaults(self):
        for key, value in self.defaults.iteritems():
            if key not in self.__dict__:
                self.__dict__[key] = value
