#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: git_push
author:
    - "Victor da Costa"
version_added: "2.9"
short_description: Push software (or files) to git repository
description:
    - Manage I(git) push of files or software to repository.
options:
    repo:
        description:
            - local repository path containing content.
        required: true
        aliases: [ name ]
    accept_hostkey:
        description:
            - if C(yes), ensure that "-o StrictHostKeyChecking=no" is
              present as an ssh option.
        type: bool
    ssh_opts:
        description:
            - Define GIT_SSH_COMMAND environment variables, which git then 
              automatically uses to override ssh arguments.
              An example value could be "-o StrictHostKeyChecking=no"
              (although this particular option is better set via
              C(accept_hostkey)).
    key_file:
        description:
            - Specify an optional private key file path, on the target host, to use for the checkout.
    remote:
        description:
            - Name of the remote.
        default: "origin"
    branch:
        description:
            - Name of the branch.
        default: "master"
    force:
        description:
            - If C(yes), will force the push operation to remote repository. 
        type: bool
    executable:
        description:
            - Path to git executable to use. If not supplied,
              the normal mechanism for resolving binary paths will be used.
requirements:
    - git>=2.3.0 (the command line tool)
notes:
    - "If the task seems to be hanging, first verify remote host is in C(known_hosts).
      SSH will prompt user to authorize the first contact with a remote host.  To avoid this prompt,
      one solution is to use the option accept_hostkey. Another solution is to
      add the remote host public key in C(/etc/ssh/ssh_known_hosts) before calling
      the git module, with the following command: ssh-keyscan -H remote_host.com >> /etc/ssh/ssh_known_hosts."
'''

EXAMPLES = '''
- name: "push local to remote"
  git_push:
    repo: "/path/to/testrepo"
    accept_hostkey: "true"
    key_file: "~/deploy_keys/testrepo"
'''

import os
import re

from pkg_resources import parse_version
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native, to_text

MIN_GIT_VERSION = '2.3.0'

def git(module):
    if module.params.get('executable'):
        return module.params.get('executable')
    else:
        return module.get_bin_path('git', required=True)

def check_git_version(module):
    """return the installed version of git"""
    cmd = "%s --version" % git(module)
    (_rc, _out, _err) = module.run_command(cmd)
    if _rc != 0:
        module.fail_json(msg=to_text(_err.strip()))

    rematch = re.search('git version (.*)$', to_native(_out))
    if not rematch:
        module.fail_json(msg='Unable to identify version of git.')
    
    if parse_version(rematch.groups()[0]) < parse_version(MIN_GIT_VERSION):
        module.fail_json(msg='Minimum git version required is %s' % MIN_GIT_VERSION)
 
    return True

def setenv_git_ssh(module):

    key_file = module.params.get('key_file')
    ssh_opts = module.params.get('ssh_opts')
    accept_hostkey = module.params.get('accept_hostkey')

    if accept_hostkey:
        if ssh_opts is not None:
            if "-o StrictHostKeyChecking=no" not in ssh_opts:
                ssh_opts += " -o StrictHostKeyChecking=no"
        else:
            ssh_opts = "-o StrictHostKeyChecking=no"

    if key_file:
        if ssh_opts is not None:
            _key_file_opts = "-i %s" % key_file
            if _key_file_opts not in ssh_opts:
                ssh_opts += " %s" % _key_file_opts
        else:
            ssh_opts = _key_file_opts

    if os.environ.has_key('GIT_SSH_COMMAND'):
        os.environ['GIT_SSH_COMMAND'] += " %s" % ssh_opts
    else:
        os.environ['GIT_SSH_COMMAND'] = ssh_opts

def git_push(module):
    _git_push = []
    _git_push.append(git(module))
    _git_push.append('push')

    if module.params.get('force'):
        _git_push.append('--force')

    _git_push.append(module.params.get('remote'))
    _git_push.append(module.params.get('branch'))

    _git_push.append("--dryrun")
    _rc, _out, _err = module.run_command(_git_push)
    if 'Everything up-to-date' not in _out:
        if not module.check_mode:
            _git_push.pop()
            _rc, _out, _err = module.run_command(_git_push)
            if _rc != 0:
                module.fail_json(msg=to_text(_err.strip()))
        return True
    
    return False

def chdir_repo(module):
    repo = module.params.get('repo')
    if os.path.exists(repo):
        os.chdir(repo)
    else:
        module.fail_json(msg='repo %s does not exist' % repo)

def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        repo=dict(type='path', aliases=['name'], required=True),
        remote=dict(type='str', default='origin', required=False),
        branch=dict(type='str', default='master', required=False),
        key_file=dict(type='path', required=False),
        accept_hostkey=dict(type='bool', required=False),
        executable=dict(type='path', required=False),
        force=dict(type='bool', required=False),
        ssh_opts=dict(type='str', required=False)
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    result = {'changed': False}

    check_git_version(module)
    chdir_repo(module)
    #setenv_git_ssh(module)
    result['changed'] = git_push(module)
    module.exit_json(**result)

if __name__ == '__main__':
    main()
