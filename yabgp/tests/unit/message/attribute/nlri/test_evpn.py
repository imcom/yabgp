# Copyright 2016 Cisco Systems, Inc.
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import unittest

from yabgp.common import constants as bgp_cons
from yabgp.message.attribute.nlri.evpn import EVPN


class TestEVPN(unittest.TestCase):
    def test_parse_mac_ip_adv(self):
        data_hex = b'\x02\x25\x00\x01\xac\x11\x00\x03\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x6c\x30\x00\x11\x22\x33\x44\x55\x20\x0b\x0b\x0b\x01\x00\x00\x00'
        data_list = [{
            'type': bgp_cons.BGPNLRI_EVPN_MAC_IP_ADVERTISEMENT,
            'value': {
                'rd': '172.17.0.3:2',
                'mac': '00-11-22-33-44-55',
                'ethernet_tag_id': 108,
                'esi': 0,
                'ip': '11.11.11.1',
                'label': [0]}
        }]
        self.assertEqual(data_list, EVPN.parse(data_hex))

    def test_construct_mac_ip_adv(self):
        data_hex = b'\x02\x25\x00\x01\xac\x11\x00\x03\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                   b'\x00\x00\x00\x6c\x30\x00\x11\x22\x33\x44\x55\x20\x0b\x0b\x0b\x01\x00\x00\x00'
        data_list = [{
            'type': bgp_cons.BGPNLRI_EVPN_MAC_IP_ADVERTISEMENT,
            'value': {
                'rd': '172.17.0.3:2',
                'mac': '00-11-22-33-44-55',
                'ethernet_tag_id': 108,
                'esi': 0,
                'ip': '11.11.11.1',
                'label': [0]}
        }]
        self.assertEqual(data_hex, EVPN.construct(data_list))


if __name__ == '__main__':
    unittest.main()
