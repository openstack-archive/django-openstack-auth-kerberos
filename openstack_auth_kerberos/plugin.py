# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import os

from django.conf import settings
from keystoneclient import auth
from keystoneclient_kerberos import v3 as v3_kerb_auth
from openstack_auth import plugin

ENV_NAME = 'KRB5CCNAME'
AUTH_SETTING_NAME = 'KERBEROS_AUTH_URL'
LOG = logging.getLogger(__name__)


class _HackedKerbAuth(v3_kerb_auth.Kerberos):

    def __init__(self, auth_url, original_auth_url, ticket):
        super(_HackedKerbAuth, self).__init__(auth_url=auth_url)
        self.original_auth_url = original_auth_url
        self.ticket = ticket

    def get_endpoint(self, session, **kwargs):
        # NOTE(jamielennox): This is a hack to return the actual AUTH_URL
        # rather than the one with the kerberos path, other wise project
        # listing tries to work on the kerberized path and will fail.
        if kwargs.get('interface') == auth.AUTH_INTERFACE:
            return self.original_auth_url

        return super(_HackedKerbAuth, self).get_endpoint(session, **kwargs)

    def get_auth_ref(self, *args, **kwargs):
        # NOTE(jamielennox): The only way to specify a ticket is in the global
        # environment. Whilst this shouldn't be an issue as has a process per
        # worker we limit so that the ticket is only in ENV for the minimum
        # time needed.
        os.environ[ENV_NAME] = self.ticket

        try:
            return super(_HackedKerbAuth, self).get_auth_ref(*args, **kwargs)
        finally:
            os.environ.pop(ENV_NAME, None)


class Kerberos(plugin.BasePlugin):

    def __init__(self, *args, **kwargs):
        super(Kerberos, self).__init__(*args, **kwargs)

        self.login_url = getattr(settings, AUTH_SETTING_NAME, None)

        if not self.login_url:
            LOG.warn('Kerberos authentication configured, but no '
                     '"%s" defined in settings.', AUTH_SETTING_NAME)

    def get_plugin(self, request=None, auth_url=None, **kwargs):
        if not (request and auth_url):
            return None

        if self.keystone_version < 3:
            return None

        if not self.login_url:
            return None

        ticket = request.environ.get(ENV_NAME)

        if not ticket:
            return None

        return _HackedKerbAuth(self.login_url, auth_url, ticket)
