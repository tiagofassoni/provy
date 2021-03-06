#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Roles in this namespace are meant to provide MySQL database management utilities for Debian distributions.
'''

import re

from provy.core import Role
from provy.more.debian.package.aptitude import AptitudeRole

class MySQLRole(Role):
    '''
    This role provides MySQL database management utilities for Debian distributions.
    <em>Sample usage</em>
    <pre class="sh_python">
        from provy.core import Role
        from provy.more.debian import MySQLRole

        class MySampleRole(Role):
            def provision(self):
                with self.using(MySQLRole) as role:
                    role.ensure_user(username=self.context['mysql_user'],
                                     identified_by=self.context['mysql_password'])

                    role.ensure_database(self.context['mysql_database'],
                                         owner=self.context['mysql_user'])

    </pre>
    '''
    def __init__(self, prov, context):
        super(MySQLRole, self).__init__(prov, context)
        self.mysql_root_user = 'root'
        self.mysql_root_pass = ''

    def provision(self):
        '''
        Installs MySQL Server and its dependencies. This method should be called upon if overriden in base classes, or MySQL won't work properly in the remote server.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    self.provision_role(MySQLRole) # no need to call this if using with block.
        </pre>
        '''
        with self.using(AptitudeRole) as role:
            self.execute('echo "mysql-server mysql-server/root_password select temppass" | debconf-set-selections',
                         stdout=False,
                         sudo=True)
            self.execute('echo "mysql-server mysql-server/root_password_again select temppass" | debconf-set-selections',
                         stdout=False,
                         sudo=True)
            result = role.ensure_package_installed('mysql-server')
            if result:
                self.execute('mysqladmin -u %s password "%s"' % (self.mysql_root_user, self.mysql_root_pass), stdout=False, sudo=True)

    def __execute_non_query(self, query):
        pass_string = ""
        if self.mysql_root_pass:
            pass_string = '--password="%s" ' % self.mysql_root_pass

        self.execute('mysql -u %s %s -e "%s" mysql' % (self.mysql_root_user, pass_string, query), stdout=False, sudo=True)

    def __execute_query(self, query):
        pass_string = ""
        if self.mysql_root_pass:
            pass_string = '--password="%s" ' % self.mysql_root_pass

        result = self.execute('mysql -u %s %s-E -e "%s" mysql' % (self.mysql_root_user, pass_string, query), stdout=False, sudo=True)
        rows = self.__get_rows(result)

        return rows

    def __get_rows(self, result):
        index_re = re.compile('(\d+)[.]')
        items = []
        item = None
        for line in result.split('\n'):
            if not line.strip():
                continue
            if line.startswith('*'):
                if item:
                    items.append(item)
                item = {
                    'index': index_re.search(line).groups()[0]
                }
            else:
                key, value = line.split(':')
                item[key.strip()] = value.strip()
        if item:
            items.append(item)

        return items

    def get_user_hosts(self, username):
        '''
        Returns all the available hosts that this user can login from.
        <em>Parameters</em>
        username - name of the user to be verified.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        if not '%' in role.get_user_hosts('someuser'):
                            # do something
        </pre>
        '''
        users = self.__execute_query("select Host from mysql.user where LOWER(User)='%s'" % username.lower())
        hosts = []
        if users:
            for user in users:
                hosts.apend(user['Host'])

        return hosts

    def user_exists(self, username, login_from='%'):
        '''
        Returns True if the given user exists for the given location in mysql server.
        <em>Parameters</em>
        username - name of the user to be verified.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        if not role.user_exists('someuser'):
                            # do something
        </pre>
        '''
        return login_from in self.get_user_hosts(username)

    def ensure_user(self, username, identified_by, login_from='%'):
        '''
        Ensure the given user is created in the database and can login from the specified location.
        <em>Parameters</em>
        username - name of the user to be created.
        identified_by - password that the user will use to login to mysql server.
        login_from - locations that this user can login from. Defaults to '%' (anywhere).
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        role.ensure_user('someuser', 'somepass', 'localhost')
        </pre>
        '''
        if not self.user_exists(username, login_from):
            self.__execute_non_query("CREATE USER '%s'@'%s' IDENTIFIED BY '%s';" % (username, login_from, identified_by))
            return True

        return False

    def is_database_present(self, database_name):
        '''
        Returns True if the database is already created.
        <em>Parameters</em>
        database_name - Database to verify.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        if role.is_database_present('database'):
                            # do something
        </pre>
        '''
        result = self.__execute_query('SHOW DATABASES')
        is_there = False
        if result:
            for row in result:
                if row['Database'].lower() == database_name.lower():
                    is_there = True

        return is_there

    def ensure_database(self, database_name):
        '''
        Creates the database if it does not exist.
        <em>Parameters</em>
        database_name - Database to create.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        role.ensure_database('database')
        </pre>
        '''
        if not self.is_database_present(database_name):
            self.__execute_non_query('CREATE DATABASE %s' % database_name)
            return True
        return False

    def get_user_grants(self, username, login_from='%'):
        '''
        Returns all grants for the given user at the given location.
        <em>Parameters</em>
        username - User to verify.
        login_from - Location to verify.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        if role.get_user_grants('user', login_from='%'):
                            # do something
        </pre>
        '''
        return_grants = []
        grants = self.__execute_query("SHOW GRANTS FOR '%s'@'%s';" % ( username, login_from))
        for grant in grants:
            return_grants.append(grant.values()[1])

        return grants

    def has_grant(self, privileges, on, username, login_from, with_grant_option):
        '''
        Returns True if the user has the specified privileges on the specified object in the given location.
        <em>Parameters</em>
        privileges - Privileges that are being verified.
        on - Database object that the user holds privileges on.
        username - User to verify.
        login_from - Location to verify.
        with_grant_option - Indicates if we are verifying against grant option.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        if role.has_grant('ALL PRIVILEGES',
                                          'database',
                                          'user',
                                          login_from='%',
                                          with_grant_option=True):
                            # do something
        </pre>
        '''

        grants = self.get_user_grants(username, login_from)
        has_grant = False
        grant_option_string = ""
        if with_grant_option:
            grant_option_string = " WITH GRANT OPTION"

        grant_string = "GRANT %s ON %s TO '%s'@'%s'%s" % (privileges, on, username, login_from, grant_option_string)
        if grant in grants:
            return True

        return False

    def ensure_grant(self, privileges, on, username, login_from="%", with_grant_option=False):
        '''
        Ensures that the given user has the given privileges on the specified location.
        <em>Parameters</em>
        privileges - Privileges to assign to user (i.e.: "ALL PRIVILEGES").
        on - Database to assign privileges to. If you want all databases pass '*.*'.
        username - User to grant the privileges to.
        login_from - Location where the user gets the grants. Defaults to '%'.
        with_grant_option - If True, indicates that this user may grant other users the same privileges. Defaults to False.
        <em>Sample usage</em>
        <pre class="sh_python">
            class MySampleRole(Role):
                def provision(self):
                    with self.using(MySQLRole) as role:
                        role.ensure_grant('ALL PRIVILEGES',
                                          on='database',
                                          username='backend',
                                          login_from'%',
                                          with_grant_option=True)
        </pre>
        '''

        if self.has_grant(privileges, on, username, login_from, with_grant_option):
            return False

        grant_option_string = ""
        if with_grant_option:
            grant_option_string = " WITH GRANT OPTION"

        grant_string = "GRANT %s ON %s TO '%s'@'%s'%s" % (privileges, on, username, login_from, grant_option_string)
        self.__execute_non_query(grant_string)

