# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import logging
import time

import requests

from iris.constants import PUSHOVER_SUPPORT

logger = logging.getLogger(__name__)


class iris_pushover(object):
    supports = frozenset([PUSHOVER_SUPPORT])

    def __init__(self, config):
        self.config = config
        self.debug = self.config.get('debug')
        self.modes = {
            'pushover': self.send_message
        }
        self.proxy = None
        if 'proxy' in self.config:
            host = self.config['proxy']['host']
            port = self.config['proxy']['port']
            self.proxy = {'http': 'http://%s:%s' % (host, port),
                          'https': 'https://%s:%s' % (host, port)}
        self.base_url = self.config.get('base_url', 'https://api.pushover.net/1').rstrip('/')
        self.message_endpoint_url = self.base_url + "/messages.json"
        self.token = self.config.get('token')
        self.title = self.config.get('title', 'Iris incident #{message.incident_id}')
        self.url_title = self.config.get('url_title', 'Open in Iris')
        self.emergency_retry = self.config.get('retry', 120)
        self.emergency_expire = self.config.get('expire', 600)
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Iris',
            'Content-Type': 'application/json'
        }
        self.timeout = config.get('timeout', 10)

    def get_message_payload(self, message, user):
        print message
        payload = {
            'token': self.token,
            'user': user,
            'title': self.title.format(message=message),
            'message': message['body']
        }

        iris_incident_url = self.config.get('iris_incident_url').rstrip('/')
        if iris_incident_url:
            payload['url'] = '%s/%s' % (iris_incident_url, message['incident_id'])
            payload['url_title'] = self.url_title

        priority = message.get('priority')
        if priority == 'urgent':
            payload['priority'] = 2
            payload['retry'] = self.emergency_retry
            payload['expire'] = self.emergency_expire
            payload['tags'] = 'incident_id:%s' % message['incident_id']
        elif priority == 'high':
            payload['priority'] = 1
        elif priority == 'low':
            payload['priority'] = -1

        return payload

    def send_message(self, message):
        start = time.time()
        payload = self.get_message_payload(message, message['destination'])
        if self.debug:
            logger.info('debug: %s', payload)
        else:
            try:
                response = requests.post(self.message_endpoint_url,
                                         headers=self.headers,
                                         json=payload,
                                         proxies=self.proxy,
                                         timeout=self.timeout)
                if response.status_code == 200 or response.status_code == 204:
                    return time.time() - start
                else:
                    logger.error('Failed to send message to Pushover: %d',
                                 response.status_code)
                    logger.error("Response: %s", response.content)
            except Exception as err:
                logger.exception('Pushover post request failed: %s', err)

    def send(self, message, customizations=None):
        return self.modes[message['mode']](message)
