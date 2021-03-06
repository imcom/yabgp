#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import os
import time
import logging
import traceback
import sys

from oslo_config import cfg

from yabgp.common import constants as bgp_cons
from yabgp.handler import BaseHandler

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


MSG_PROCESS_OPTS = [
    cfg.BoolOpt('write_disk',
                default=True,
                help='Whether the BGP message is written to disk'),
    cfg.StrOpt('write_dir',
               default=os.path.join(os.environ['HOME'], 'data/bgp/'),
               help='The BGP messages storage path'),
    cfg.IntOpt('write_msg_max_size',
               default=500,
               help='The Max size of one BGP message file, the unit is MB'),
    cfg.BoolOpt('write_keepalive',
                default=False,
                help='Whether write keepalive message to disk')
]

CONF.register_opts(MSG_PROCESS_OPTS, group='message')


class Handler(BaseHandler):
    def __init__(self):
        super(Handler, self).__init__()
        '''
            {<peer>: (<path>, <current file>)}
        '''
        self.peer_files = {}
        '''
            {<peer>: <seq number>}
        '''
        self.msg_sequence = {}

    def init_msg_file(self, peer_addr):
        msg_file_path_for_peer = os.path.join(
            CONF.message.write_dir,
            peer_addr
        )
        if not os.path.exists(msg_file_path_for_peer):
            os.makedirs(msg_file_path_for_peer)
            LOG.info('Create dir %s for peer %s', msg_file_path_for_peer, peer_addr)
        LOG.info('BGP message file path is %s', msg_file_path_for_peer)

        if msg_file_path_for_peer and peer_addr not in self.peer_files:
            msg_path = msg_file_path_for_peer + '/msg/'
            if not os.path.exists(msg_path):
                os.makedirs(msg_path)

            # try get latest file and msg sequence if any
            last_msg_seq, msg_file_name = Handler.get_last_seq_and_file(msg_path)

            if not msg_file_name:
                msg_file_name = "%s.msg" % time.time()
            # store the message sequence
            self.msg_sequence[peer_addr] = last_msg_seq + 1
            msg_file = open(os.path.join(msg_path, msg_file_name), 'a')
            msg_file.flush()
            self.peer_files[peer_addr] = (msg_path, msg_file)
            LOG.info('BGP message file %s', msg_file_name)
            LOG.info('The last bgp message seq number is %s', last_msg_seq)

    @staticmethod
    def get_last_seq_and_file(msg_path):
        """
        Get the last sequence number in the latest log file.
        """
        LOG.info('get the last bgp message seq for this peer')
        last_seq = 0
        # first get the last file
        file_list = os.listdir(msg_path)
        if not file_list:
            return last_seq, None
        file_list.sort()
        msg_file_name = file_list[-1]
        try:
            with open(msg_path + msg_file_name, 'rb') as fh:
                line = None
                for line in fh:
                    pass
                last = line
                if line:
                    if last.startswith('['):
                        last_seq = eval(last)[1]
                    elif last.startswith('{'):
                        last_seq = json.loads(last)['seq']
        except OSError:
            LOG.error('Error when reading bgp message files')
        except Exception as e:
            LOG.debug(traceback.format_exc())
            LOG.error(e)
            sys.exit()

        return last_seq, msg_file_name

    def write_msg(self, peer, timestamp, msg_type, msg, flush=False):
        """
        write bgp message into local disk file
        :param peer: peer address
        :param timestamp: timestamp
        :param msg_type: message type (0,1,2,3,4,5,6)
        :param msg: message dict
        :param msg_path: path to store messages on disk
        :param flush: flush after write or not
        :return:
        """
        msg_path, msg_file = self.peer_files.get(peer.lower(), (None, None))
        if msg_path:
            msg_seq = self.msg_sequence[peer.lower()]

            msg_record = {
                't': timestamp,
                'seq': msg_seq,
                'type': msg_type
            }
            msg_record.update(msg)
            json.dump(msg_record, msg_file)
            msg_file.write('\n')
            self.msg_sequence[peer.lower()] += 1
            if flush:
                msg_file.flush()

    def flush_and_check_file_size(self, peer):
        msg_path, cur_file = self.peer_files.get(peer.lower(), (None, None))
        if msg_path:
            # Flush message log file
            cur_file.flush()

            # if the size of the msg file is bigger than 'max_msg_file_size',
            # then save as and re-open a new file.
            if os.path.getsize(cur_file.name) >= CONF.message.write_msg_max_size:
                cur_file.close()
                msg_file_name = "%s.msg" % time.time()
                LOG.info('Open a new message file %s', msg_file_name)
                msg_file = open(os.path.join(msg_path + msg_file_name), 'a')
                self.peer_files[peer.lower()] = (msg_path, msg_file)
                return True
        return False

    def on_update_error(self, peer, timestamp, msg):
        self.write_msg(
            peer=peer.factory.peer_addr,
            timestamp=timestamp,
            msg_type=6,
            msg={'msg': msg},
            flush=True
        )

    def update_received(self, peer, timestamp, msg):
        # write message to disk
        self.write_msg(
            peer=peer.factory.peer_addr,
            timestamp=timestamp,
            msg_type=bgp_cons.MSG_UPDATE,
            msg={"msg": msg}
        )
        self.flush_and_check_file_size(peer.factory.peer_addr)

    def keepalive_received(self, peer, timestamp):
        """
        keepalive message default handler
        :param peer:
        :param timestamp:
        :return:
        """

        if peer.msg_recv_stat['Keepalives'] == 1:
            # do something with the connection establish event
            pass

        if CONF.message.write_keepalive:
            # write bgp message
            self.write_msg(
                peer=peer.factory.peer_addr,
                timestamp=timestamp,
                msg_type=4,
                msg={"msg": None},
                flush=True
            )

    def open_received(self, peer, timestamp, result):
        # write bgp message
        self.write_msg(
            peer=peer.factory.peer_addr,
            timestamp=timestamp,
            msg_type=1,
            msg={"msg": result},
            flush=True
        )

    def route_refresh_received(self, peer, msg, msg_type):
        self.write_msg(
            peer=peer.factory.peer_addr,
            timestamp=time.time(),
            msg_type=msg_type,
            msg={"msg": msg},
            flush=True
        )

    def notification_received(self, peer, msg):
        self.write_msg(
            peer=peer.factory.peer_addr,
            timestamp=time.time(),
            msg_type=3,
            msg={"msg": msg},
            flush=True
        )

    def on_connection_lost(self, peer):
        self.write_msg(
            peer=peer.factory.peer_addr,
            timestamp=time.time(),
            msg_type=bgp_cons.MSG_BGP_CLOSED,
            msg={"msg": None},
            flush=True
        )

    def on_connection_failed(self, peer, msg):
        self.write_msg(
            peer=peer,
            timestamp=time.time(),
            msg_type=0,
            msg={"msg": msg}
        )
