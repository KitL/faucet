# Copyright (C) 2015 Brad Cowie, Christopher Lorier and Joe Stringer.
# Copyright (C) 2015 Research and Education Advanced Network New Zealand Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import logging
import yaml
from valve import valve_factory
from poller import gauge_factory
from dp import DP
from gauge_config import GaugeConfig

def get_logger(logname):
    return logging.getLogger(logname + '.config')

def read_config(config_file, logname):
    logger = get_logger(logname)
    try:
        with open(config_file, 'r') as stream:
            conf = yaml.load(stream)
    except yaml.YAMLError as ex:
        mark = ex.problem_mark
        errormsg = "Error in file: {0} at ({1}, {2})".format(
            config_file,
            mark.line + 1,
            mark.column + 1)
        logger.error(errormsg)
        return None
    return conf

    @classmethod
    def _parser_v2(cls, conf, config_file, logname):
        logger = logging.getLogger(logname)

        if 'dps' not in conf:
            logger.error("dps not configured in file: {0}".format(config_file))
            return None

        vlans = conf.pop('vlans', {})
        acls = conf.pop('acls', {})

        dps = []
        for dp_id, cf in conf['dps'].iteritems():
            dp = DP(dp_id, logname)
            interfaces = cf.pop('interfaces', {})
            dp.__dict__.update(cf)
            dp.set_defaults()

            for vid, vlan_conf in vlans.iteritems():
                dp.add_vlan(vid, vlan_conf)
            for port_num, port_conf in interfaces.iteritems():
                dp.add_port(port_num, port_conf)
            for acl_num, acl_conf in acls.iteritems():
                dp.add_acl(acl_num, acl_conf)

            dps.append(dp)

        if dps:
            return dps[0]
        else:
            logger.error("dps configured with no elements in file: {0}".format(config_file))
            return None

    @classmethod
    def parser(cls, config_file, logname=__name__):
        try:
            with open(config_file, 'r') as stream:
                conf = yaml.load(stream)
        except yaml.YAMLError as ex:
            mark = ex.problem_mark
            logger.error("Error in file: {0} at ({1}, {2})".format(
                config_file,
                mark.line + 1,
                mark.column + 1))
            return None

def dp_parser(config_file, logname):
    logger = logging.getLogger(logname)
    conf = read_config(config_file, logname)
    if conf is None:
        return None

    version = conf.pop('version', 1)

    if version == 1:
        return _dp_parser_v1(conf, config_file, logname)
    elif version == 2:
        return _dp_parser_v2(conf, config_file, logname)
    else:
        logger.error("unsupported config version number: {0}".format(version))
        return None

def _dp_parser_v1(conf, config_file, logname):
    logger = logging.getLogger(logname)

    # TODO: warn when the configuration contains meaningless elements
    # they are probably typos

    dp_id = conf['dp_id']

    interfaces = conf.pop('interfaces', {})
    vlans = conf.pop('vlans', {})
    acls = conf.pop('acls', {})

    dp = DP(dp_id, conf)
    try:
        dp.sanity_check()
    except AssertionError as err:
        self.logger.exception("Error in config file: {0}".format(err))
        return None

    for vid, vlan_conf in vlans.iteritems():
        dp.add_vlan(vid, vlan_conf)
    for port_num, port_conf in interfaces.iteritems():
        dp.add_port(port_num, port_conf)
    for acl_num, acl_conf in acls.iteritems():
        dp.add_acl(acl_num, acl_conf)

    return dp

def _dp_parser_v2(cls, conf, config_file, logname):
    logger = logging.getLogger(logname)

    if 'dps' not in conf:
        logger.error("dps not configured in file: {0}".format(config_file))
        return None

    vlans = conf.pop('vlans', {})
    acls = conf.pop('acls', {})

    dps = {}
    for dp_id, dp_conf in conf['dps'].iteritems():
        dp = DP(dp_id, logname)
        interfaces = dp_conf.pop('interfaces', {})
        dp.update(dp_conf)
        dp.set_defaults()

        for vid, vlan_conf in vlans.iteritems():
            dp.add_vlan(vid, vlan_conf)
        for port_num, port_conf in interfaces.iteritems():
            dp.add_port(port_num, port_conf)
        for acl_num, acl_conf in acls.iteritems():
            dp.add_acl(acl_num, acl_conf)

        dps[dp_id] = dp

    if dps:
        return dps.itervalues()[0]
    else:
        logger.error("dps configured with no elements in file: {0}".format(config_file))
        return None

def valve_parser(config_file, logname):
    dp = dp_parser(config_file, logname)
    return valve_factory(dp.hardware)(dp, logname)

def gauge_conf_parser(config_file, logname):
    logger = get_logger(logname)

def gauge_parser(config_file, logname):
    #TODO: make this backwards compatible
    logger = get_logger(logname)

    conf = read_config(config_file, logname)
    if conf is None:
        return None

    result = {}

    valves = {}
    for valve_file in conf['valve_configs']:
        dp = dp_parser(valve_file, logname)
        valves[dp.dp_id] = dp

    for dictionary in conf['gauges']:
        for dp_id in dictionary['dps']:
            if dp_id not in valves:
                errormsg = "dp_id: {0} metered but not configured".format(
                    dp_id
                    )
                logger.error(errormsg)
                continue

            dp = valves[dp_id]

            gauge_conf = GaugeConfig(dictionary)

            result.setdefault(dp_id, {})

            gauge_type = gauge_conf.gauge_type
            if gauge_conf.influx_stats:
                gauge_type += '_influx'

            # Note the use of gauge_conf.gauge_type for the key and gauge_type
            # for the factory. This is so gauge can find the appropriate gauge
            # more simply.
            gauge = gauge_factory(gauge_type)(dp, gauge_conf, logname)
            if gauge is None:
                logging.error('invalid gauge config {0} {1}'.format(
                    dp_id, gauge_conf.gauge_type))
                continue
            result[dp_id][gauge_conf.gauge_type] = gauge

    return result
