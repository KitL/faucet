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
from watcher import watcher_factory
from dp import DP
from watcher_conf import WatcherConf

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
    try:
        dp.sanity_check()
    except AssertionError as err:
        self.logger.exception("Error in config file: {0}".format(err))
        return None

    for identifier, dp_conf in conf['dps'].iteritems():
        interfaces = dp_conf.pop('interfaces', {})

        dp = DP(identifier, dp_conf)
        for v_identifier, vlan_conf in vlans.iteritems():
            dp.add_vlan(v_identifier, vlan_conf)
        for p_identifier, port_conf in interfaces.iteritems():
            dp.add_port(p_identifier, port_conf)
        for a_identifier, acl_conf in acls.iteritems():
            dp.add_acl(a_identifier, acl_conf)

        dps[dp_id] = dp

    if dps:
        return dps.itervalues()[0]
    else:
        logger.error("dps configured with no elements in file: {0}".format(config_file))
        return None

def valve_parser(config_file, logname):
    dp = dp_parser(config_file, logname)
    return valve_factory(dp.hardware)(dp, logname)

def watcher_parser(config_file, logname):
    #TODO: make this backwards compatible
    logger = get_logger(logname)
    logging.info("here I am")

    conf = read_config(config_file, logname)
    if conf is None:
        return None

    result = {}

    dps = {}
    for faucet_file in conf['faucet_configs']:
        dp = dp_parser(faucet_file, logname)
        dps[dp.name] = dp

    dbs = conf.pop('dbs')

    for name, dictionary in conf['watchers'].iteritems():
        for dp_name in dictionary['dps']:
            if dp_name not in dps:
                errormsg = "dp: {0} metered but not configured".format(
                    dp_name
                    )
                logger.error(errormsg)
                continue

            dp = dps[dp_name]
            dp_id = dp.dp_id
            result.setdefault(dp_id, {})

            watcher_conf = WatcherConf(name, dictionary)
            print dbs[watcher_conf.db]
            watcher_conf.add_db(dbs[watcher_conf.db])

            watcher = watcher_factory(watcher_conf)(dp, watcher_conf, logname)
            if watcher is None:
                logging.error('invalid watcher configuration {0} {1}'.format(
                    dp_name, watcher_conf.name))
                continue
            result[dp_id][watcher_conf.type] = watcher

    return result
