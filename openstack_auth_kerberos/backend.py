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

import os

from keystoneclient import auth
from keystoneclient_kerberos import v3 as v3_kerb_auth
from openstack_auth import base


class _HackedKerbAuth(v3_kerb_auth.Kerberos):

    def __init__(self, auth_url, original_auth_url):
        self.original_auth_url = original_auth_url
        super(_HackedKerbAuth, self).__init__(auth_url=auth_url)

    def get_endpoint(self, session, **kwargs):
        # NOTE(jamielennox): This is a hack to return the actual AUTH_URL
        # rather than the one with the kerberos path, other wise project
        # listing tries to work on the kerberized path and will fail.
        if kwargs.get('interface') == auth.AUTH_INTERFACE:
            return self.original_auth_url

        return super(_HackedKerbAuth, self).get_endpoint(session, **kwargs)



class KerberosLogin(base.BaseIdentityAuthentication):

    def get_unscoped_plugin(self, request=None, auth_url=None, **kwargs):
        if not request:
            return None

        if self.keystone_version < 3:
            return None

        ticket = request.environ.get('KRB5CCNAME')

        if not ticket:
            return None

        os.environ['KRB5CCNAME'] = ticket

        original_auth_url = auth_url

        # FIXME(jamielennox): get this from settings
        s = auth_url.split('/')
        s.insert(-1, 'krb')
        auth_url = '/'.join(s)

        return _HackedKerbAuth(auth_url, original_auth_url)
