==============
 Installation
==============

Installation of the module can be done using pip on the command line::

    $ pip install django-openstack-auth-kerberos


=============
Configuration
=============

The configuration process for kerberos authentication is somewhat complex as it
relies on coordination between settings in HTTPd, horizon, and site specific
customizations.

Kerberos authentication relies upon the server supporting S4U2 proxying. The
configuration of which is beyond this guide however for a introduction you can
use `this tutorial`_.

.. _this tutorial: http://www.jamielennox.net/blog/2015/02/27/setting-up-s4u2proxy/

Configuring Keystone
--------------------

Currently kerberos authentication is designed to support having keystone
mounted at a path that is protected by kerberos.  A guide to setting up
keystone in this manner with a special kerberos path `can be found here`_.

.. _can be found here: http://www.jamielennox.net/blog/2015/02/12/step-by-step-kerberized-keystone/

Configuring Horizon
-------------------

There are two parts to configuring horizon, we must install the kerberos
authentication backend and add new views that will trigger these backends.

We create the additional `/auth/kerberos` route by adding
:py:mod:`openstack_auth_kerberos.urls` to `AUTHENTICATION_URLS`_.  Remember to
include the default password backend as we are overriding this value::

    AUTHENTICATION_URLS = ('openstack_auth.urls',
                           'openstack_auth_kerberos.urls')

We install the additional :py:class:`~openstack_auth_kerberos.plugin.Kerberos`
handlers that will be triggered by the `/auth/kerberos` route by installing the
kerberos authentication plugin. Again remember to include the standard
username/password authentication plugin::

    AUTHENTICATION_PLUGINS = ('openstack_auth.plugin.password.PasswordPlugin',
                              'openstack_auth_kerberos.plugin.Kerberos')

Configuring Plugin
------------------

Because kerberized keystone is mounted on a path other than the
`OPENSTACK_KEYSTONE_URL`_ we need to indicate the kerberized auth path to the
plugin with the `KERBEROS_AUTH_URL` setting::

    KERBEROS_AUTH_URL = 'http://%s:5000/krb/v3' % OPENSTACK_HOST

Configuring Apache
------------------

Apache should be configured as a S4U2 proxy on the `/auth/kerberos` location.
Beyond this there are a couple of extra configuration points.

Kerberos Fallback
+++++++++++++++++

If kerberos authentication fails then we would like the server to present the
standard horizon login page. To do this we define an `ErrorDocument`_. This
document is rendered and returned as the body of the initial 401 Unauthorized
response which is a standard part of SPNEGO/kerberos negotiation.

It is a limitation of the way httpd and django work that we cannot redirect the
`ErrorDocument`_ to a generated URL. We therefore specify a static HTML page
which will be used as a bouncing page to send users to the standard login page
when kerberos authentication fails.

The default bouncing page is:

.. literalinclude:: ../../data/login-redirect.html
    :language: html

This page provides a javascript redirect to the `/auth/login` path (the horizon
default login) which will be triggered if the kerberos handler is not present.
If your `LOGIN_URL` is defined as something other that `/auth/login` you should
update this snippet accordingly.

The easiest way to deploy this is to copy the html file to the `STATIC_ROOT`_
of your deployment and set the `ErrorDocument`_ to the publicly accessible URL::

    <Location /auth/kerberos>
        ...
        ErrorDocument 401 "/media/login-redirect.html"
    </Location>

Sample Config
+++++++++++++

An example of a full `/etc/httpd/conf.d/horizon.conf` file::

    <VirtualHost *:80>
        WSGIScriptAlias / /opt/horizon/openstack_dashboard/wsgi/django.wsgi
        WSGIDaemonProcess horizon user=apache group=apache processes=3 threads=10 home=/opt/horizon display-name=apached
        WSGIApplicationGroup %{GLOBAL}

        SetEnv APACHE_RUN_USER apached
        SetEnv APACHE_RUN_GROUP apache
        WSGIProcessGroup horizon

        DocumentRoot /opt/horizon/.blackhole/
        Alias /media /opt/horizon/openstack_dashboard/static

        <Directory />
            Options FollowSymLinks
            AllowOverride None
        </Directory>

        <Directory /opt/horizon/>
            Options Indexes FollowSymLinks MultiViews
            AllowOverride None
            <IfVersion < 2.4>
                Order allow,deny
                Allow from all
            </IfVersion>
            <IfVersion >= 2.4>
                Require all granted
            </IfVersion>
        </Directory>

        <Location "/auth/krb/">
            AuthType Kerberos
            AuthName "Kerberos Login"
            KrbMethodNegotiate on
            KrbMethodK5Passwd off
            KrbServiceName HTTP
            KrbAuthRealms MY.REALM.ORG
            Krb5KeyTab /etc/httpd/conf/httpd.keytab
            KrbSaveCredentials on
            KrbLocalUserMapping on
            Require valid-user
            KrbConstrainedDelegation on
            ErrorDocument 401 "/media/login-redirect.html"
        </Location>

        ErrorLog /var/log/httpd/horizon_error.log
        CustomLog /var/log/httpd/horizon_access.log combined
    </VirtualHost>

    WSGISocketPrefix /var/run/httpd


.. _AUTHENTICATION_URLS: http://docs.openstack.org/developer/horizon/topics/settings.html#authentication-urls
.. _OPENSTACK_KEYSTONE_URL: http://docs.openstack.org/developer/horizon/topics/settings.html#openstack-keystone-url
.. _STATIC_ROOT: https://docs.djangoproject.com/en/1.6/ref/settings/#std:setting-STATIC_ROOT
.. _ErrorDocument: https://httpd.apache.org/docs/2.4/custom-error.html
