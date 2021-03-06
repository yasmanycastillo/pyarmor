#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#############################################################
#                                                           #
#      Copyright @ 2018 -  Dashingsoft corp.                #
#      All rights reserved.                                 #
#                                                           #
#      pyarmor                                              #
#                                                           #
#      Version: 3.4.0 -                                     #
#                                                           #
#############################################################
#
#
#  @File: pyarmor.py
#
#  @Author: Jondy Zhao(jondy.zhao@gmail.com)
#
#  @Create Date: 2018/01/17
#
#  @Description:
#
#   A tool used to import or run obfuscated python scripts.
#

'''See "pyarmor.py <command> -h" for more information on a specific command.'''

import json
import logging
import os
import shutil
import subprocess
import sys
import time

try:
    import argparse
except ImportError:
    # argparse is new in version 2.7
    import polyfills.argparse as argparse

from config import  version, version_info, trial_info, \
                    platform, dll_ext, dll_name, \
                    default_obf_module_mode, default_obf_code_mode, \
                    config_filename, capsule_filename, license_filename

from project import Project
from utils import make_capsule, obfuscate_scripts, make_runtime, \
                  make_project_license, make_entry, show_hd_info, \
                  build_path, make_command, get_registration_code

def armorcommand(func):
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(e)
    wrap.__doc__ = func.__doc__
    return wrap

@armorcommand
def _init(args):
    '''Create an empty project or reinitialize an existing one

This command creates an empty project in the specified path -
basically a configure file .pyarmor_config, a project capsule
.pyarmor_capsule.zip, and a shell script "pyarmor" will be created.

Option --src specifies where to find python source files. By default,
  all .py files in this directory will be included in this project.

Option --entry specifies main script, which could be run directly
after obfuscated.

EXAMPLES

    python pyarmor.py init --src=examples --entry=queens.py project1
    cd project1/
    ./pyarmor info

    '''
    path = args.project
    logging.info('Create project in %s ...', path)

    if not os.path.exists(path):
        logging.info('Make project directory %s', path)
        os.makedirs(path)

    src = os.path.abspath(args.src)
    logging.info('Python scripts base path: %s', src)

    name = os.path.basename(os.path.abspath(path))
    project = Project(name=name, title=name, src=src, entry=args.entry)

    logging.info('Create configure file ...')
    filename = os.path.join(path, config_filename)
    project.save(path)
    logging.info('Configure file %s created', filename)

    logging.info('Create project capsule ...')
    filename = os.path.join(path, capsule_filename)
    make_capsule(filename)
    logging.info('Project capsule %s created', filename)

    logging.info('Create pyarmor command ...')
    script = make_command(platform, sys.executable, sys.argv[0], path)
    logging.info('Pyarmor command %s created', script)

    logging.info('Project init successfully.')

@armorcommand
def _update(args):
    '''Update project settings.

Option --manifest is comma-separated list of manifest template
command, same as MANIFEST.in of Python Distutils. The default value is
"global-include *.py"

Option --entry is comma-separated list of entry scripts, relative to
src path of project.

Examples,

    cd projects/project1
    ./pyarmor config --entry "main.py, another/main.py"
                     --manifest "global-include *.py, exclude test*.py"

    '''
    project = Project()
    project.open(args.project)
    logging.info('Update project %s ...', args.project)

    if args.src is not None:
        args.src = os.path.abspath(args.src)
    keys = project._update(dict(args._get_kwargs()))
    logging.info('Changed attributes: %s', keys)

    project.save(args.project)
    logging.info('Update project OK.')

@armorcommand
def _info(args):
    '''Show project information'''
    project = Project()
    project.open(args.project)
    logging.info('Project %s information\n%s', args.project, project.info())

@armorcommand
def _build(args):
    '''Build project, obfuscate all files in the project'''
    project = Project()
    project.open(args.project)
    logging.info('Build project %s ...', args.project)
    capsule = build_path(project.capsule, args.project)

    if not args.only_runtime:
        output = project.output
        mode = project.get_obfuscate_mode()
        files = project.get_build_files(args.force)
        src = project.src
        filepairs = [(os.path.join(src, x), os.path.join(output, x))
                     for x in files]

        logging.info('%s increment build',
                     'Disable' if args.force else 'Enable')
        logging.info('Search scripts from %s', src)
        logging.info('Obfuscate %d scripts with mode %s', len(files), mode)
        for x in files:
            logging.info('\t%s', x)
        logging.info('Save obfuscated scripts to %s', output)

        obfuscate_scripts(filepairs, mode, capsule, output)

        # for x in targets:
        #     output = os.path.join(project.output, x)
        #     pairs = [(os.path.join(src, x), os.path.join(output, x))
        #              for x in files]
        #     for src, dst in pairs:
        #         try:
        #             shutil.copy2(src, dst)
        #         except Exception:
        #             os.makedirs(os.path.dirname(dst))
        #             shutil.copy2(src, dst)
        project['build_time'] = time.time()
        project.save(args.project)

    if not args.no_runtime:
        logging.info('Make runtime files')
        make_runtime(capsule, output)

    if project.entry:
        for x in project.entry.split(','):
            filename = os.path.join(output, x.strip())
            logging.info('Update entry script %s', filename)
            make_entry(filename, project.runtime_path)
    else:
        logging.info('\tIn order to import obfuscated scripts, insert ')
        logging.info('\t2 lines in entry script:')
        logging.info('\t\tfrom pytransfrom import pyarmor_runtime')
        logging.info('\t\tpyarmor_runtime()')

    logging.info('Build project OK.')

@armorcommand
def _licenses(args):
    '''Generate licenses for this project.

Use command hdinfo to get hardware information.
    '''
    logging.info('Generate licenses for project %s ...', args.project)

    if args.expired is None:
        fmt = ''
    else:
        fmt = '*TIME:%.0f\n' % \
              time.mktime(time.strptime(args.expired, '%Y-%m-%d'))

    if args.bind_disk:
        fmt = '%s*HARDDISK:%s' % (fmt, args.bind_disk)

    if args.bind_mac:
        fmt = '%s*IFMAC:%s' % (fmt, args.bind_mac)

    if args.bind_ipv4:
        fmt = '%s*IFIPV4:%s' % (fmt, args.bind_ipv4)

    # if args.bind_ipv6:
    #     fmt = '%s*IFIPV6:%s' % (fmt, args.bind_ipv6)

    if args.bind_domain:
        fmt = '%s*DOMAIN:%s' % (fmt, args.bind_domain)

    # if args.bind_file:
    #     if os.path.exists(args.bind_file):
    #         f = open(args.bind_file, 'rb')
    #         s = f.read()
    #         f.close()
    #         if sys.version_info[0] == 3:
    #             fmt = '%s*FIXKEY:%s;%s' % (fmt, key, s.decode())
    #         else:
    #             fmt = '%s*FIXKEY:%s;%s' % (fmt, key, s)
    #     else:
    #         raise RuntimeError('Bind file %s not found' % bindfile)

    project = Project()
    project.open(args.project)

    licpath = os.path.join(args.project, 'licenses')
    if not os.path.exists(licpath):
        logging.info('Make output path of licenses: %s', licpath)
        os.mkdir(licpath)

    # Prefix of registration code
    fmt = fmt + '*CODE:'
    capsule = build_path(project.capsule, args.project)
    for rcode in args.codes:
        output = os.path.join(licpath, rcode)
        if not os.path.exists(output):
            logging.info('Make path: %s', output)
            os.mkdir(output)

        licfile = os.path.join(output, license_filename)
        licode = fmt + rcode
        txtcode = licode.replace('\n', r'\n')
        if args.expired:
            txtcode = '"Expired:%s%s"' % (args.expired,
                                          txtcode[txtcode.find(r'\n')+2:])
        logging.info('Generate license: %s', txtcode)
        make_project_license(capsule, licode, licfile)
        logging.info('Write license file: %s', licfile)

        logging.info('Write information to %s.txt', licfile)
        with open(os.path.join(licfile + '.txt'), 'w') as f:
            f.write(txtcode)

    logging.info('Generate %d licenses OK.', len(args.codes))

@armorcommand
def _target(args):
    project = Project()
    project.open(args.project)

    name = args.name[0]
    if args.remove:
        logging.info('Remove target from project %s ...', args.project)
        project.remove_target(name)
    else:
        logging.info('Add target to project %s ...', args.project)
        project.add_target(name, args.platform, args.license)
    project.save(args.project)

@armorcommand
def _obfuscate(args):
    '''Obfuscate scripts without project'''
    path = args.src
    logging.info('Obfuscate scripts in path "%s" ...', path)

    capsule = os.path.join(path, capsule_filename)
    if not os.path.exists(capsule):
        logging.info('Generate capsule %s', capsule)
        make_capsule(capsule)

    output = args.output
    files = Project.build_globfiles(args.patterns, path)
    filepairs = [(os.path.join(path, x), os.path.join(output, x))
                 for x in files]
    mode = Project.map_obfuscate_mode(default_obf_module_mode,
                                      default_obf_code_mode)

    logging.info('Obfuscate scripts with mode %s', mode)
    logging.info('Save obfuscated scripts to "%s"', output)
    for a, b in filepairs:
        logging.info('\t%s -> %s', a, b)
    obfuscate_scripts(filepairs, mode, capsule, output)

    logging.info('Make runtime files')
    make_runtime(capsule, output)

    for entry in args.entry.split(','):
        filename = os.path.join(output, entry.strip())
        if not os.path.exists(filename):
            shutil.copy(os.path.join(path, entry.strip()), filename)
        logging.info('Update entry script %s', filename)
        make_entry(filename)

    logging.info('Obfuscate %d scripts OK.', len(files))

@armorcommand
def _check(args):
    '''Check consistency of project'''
    project = Project()
    project.open(args.project)
    logging.info('Check project %s ...', args.project)
    project._check(args.project)
    logging.info('Check project OK.')

@armorcommand
def _benchmark(args):
    '''Run benchmark test in current machine'''
    logging.info('Start benchmark test ...')
    logging.info('Obfuscate module mode: %s', args.obf_module_mode)
    logging.info('Obfuscate bytecode mode: %s', args.obf_code_mode)

    logging.info('Benchmark bootstrap ...')
    mode = Project.map_obfuscate_mode(args.obf_module_mode,
                                      args.obf_code_mode)
    p = subprocess.Popen(
        [sys.executable, 'benchmark.py', 'bootstrap', str(mode)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    logging.info('Benchmark bootstrap OK.')

    logging.info('Run benchmark test ...')
    p = subprocess.Popen([sys.executable, 'benchmark.py'], cwd='.benchtest')
    p.wait()

    logging.info('Finish benchmark test.')

@armorcommand
def _hdinfo(args):
    show_hd_info()

def _version_info():
    if get_registration_code() == '':
        return 'Pyarmor Trial Version %s\n%s' % (version, trial_info)
    else:
        return 'Pyarmor Version %s\n' % version

def main(args):
    parser = argparse.ArgumentParser(
        prog='pyarmor.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='pyarmor used to import or run obfuscated python scripts.',
        epilog=__doc__,
    )
    parser.add_argument('-v', '--version', action='version',
                        version=_version_info())

    subparsers = parser.add_subparsers(
        title='The most commonly used pyarmor commands are',
        metavar='<command>'
    )

    #
    # Command: obfuscate
    #
    cparser = subparsers.add_parser(
        'obfuscate',
        epilog=_obfuscate.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Obfuscate python scripts')
    cparser.add_argument('--output', default='dist', metavar='PATH')
    cparser.add_argument('--entry', metavar='SCRIPT', help='Entry script')
    cparser.add_argument('--src', required=True,
                         help='Base path for matching python scripts')
    cparser.add_argument('patterns', nargs='*', default=['*.py'],
                         help='File patterns, default is "*.py"')
    cparser.set_defaults(func=_obfuscate)

    #
    # Command: init
    #
    cparser = subparsers.add_parser(
        'init',
        epilog=_init.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Create an empty project to manage obfuscated scripts'
    )
    cparser.add_argument('--entry',
                         help='Entry script of this project')
    cparser.add_argument('--src', required=True,
                         help='Base path of python scripts')
    cparser.add_argument('project', nargs='?', help='Project path')
    cparser.set_defaults(func=_init)


    #
    # Command: config
    #
    cparser = subparsers.add_parser(
        'config',
        epilog=_update.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Update project information')
    cparser.add_argument('project', nargs='?', metavar='PATH',
                         default='', help='Project path')
    cparser.add_argument('--name')
    cparser.add_argument('--src')
    cparser.add_argument('--output')
    cparser.add_argument('--manifest', metavar='TEMPLATE',
                         help='Manifest template string')
    cparser.add_argument('--entry', metavar='SCRIPT',
                         help='Entry script of this project')
    cparser.add_argument('--obf-module-mode',
                         choices=Project.OBF_MODULE_MODE)
    cparser.add_argument('--obf-code-mode',
                         choices=Project.OBF_CODE_MODE)
    cparser.add_argument('--runtime-path', metavar="RPATH")
    cparser.set_defaults(func=_update)

    #
    # Command: info
    #
    cparser = subparsers.add_parser(
        'info',
        epilog=_info.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Show project information'
    )
    cparser.add_argument('project', nargs='?', metavar='PATH',
                         default='', help='Project path')
    cparser.set_defaults(func=_info)

    #
    # Command: check
    #
    cparser = subparsers.add_parser(
        'check',
        epilog=_check.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Check consistency of project')
    cparser.add_argument('project', nargs='?', metavar='PATH',
                         default='', help='Project path')
    cparser.set_defaults(func=_check)

    #
    # Command: build
    #
    cparser = subparsers.add_parser(
        'build',
        epilog=_build.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Build project, obfuscate all the scripts in the project')
    cparser.add_argument('project', nargs='?', metavar='PATH', default='',
                         help='Project path')
    cparser.add_argument('-B', '--force', action='store_true',
                         help='Obfuscate all scripts even if it\'s not updated')
    cparser.add_argument('-r', '--only-runtime', action='store_true',
                         help='Generate extra runtime files only')
    cparser.add_argument('-n', '--no-runtime', action='store_true',
                         help='DO NOT generate extra runtime files')
    cparser.set_defaults(func=_build)

    #
    # Command: target
    #
    # cparser = subparsers.add_parser('target', help='Manage target for project')
    # cparser.add_argument('name', metavar='NAME', nargs=1,
    #                      help='Target name')
    # group = cparser.add_argument_group('Target definition')
    # group.add_argument('-p', '--platform', metavar='PLATFORM',
    #                    help='Target platform to run obfuscated scripts')
    # group.add_argument('-c', '--license', metavar='CODE',
    #                    help='License code for this target')
    # cparser.add_argument('--remove', action='store_true',
    #                      help='Remove target from project')
    # cparser.add_argument('-P', '--project', required=True, default='',
    #                      help='Project path or configure file')
    # cparser.set_defaults(func=_target)

    #
    # Command: license
    #
    cparser = subparsers.add_parser(
        'licenses',
        epilog=_licenses.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Generate batch licenses for project'
    )
    cparser.add_argument('codes', nargs='+', metavar='CODE',
                         help='Registration code for this license')
    group = cparser.add_argument_group('Bind license to hardware')
    group.add_argument('-e', '--expired', metavar='YYYY-MM-DD',
                       help='Expired date for this license')
    group.add_argument('-d', '--bind-disk', metavar='SN',
                       help='Bind license to serial number of harddisk')
    group.add_argument('-4', '--bind-ipv4', metavar='a.b.c.d',
                       help='Bind license to ipv4 addr')
    # group.add_argument('-6', '--bind-ipv6', metavar='a:b:c:d',
    #                    help='Bind license to ipv6 addr')
    group.add_argument('-m', '--bind-mac', metavar='x:x:x:x',
                       help='Bind license to mac addr')
    group.add_argument('--bind-domain', metavar='DOMAIN',
                       help='Bind license to domain name')
    cparser.add_argument('-P', '--project', default='', help='Project path')
    cparser.set_defaults(func=_licenses)

    #
    # Command: hdinfo
    #
    cparser = subparsers.add_parser(
        'hdinfo',
        epilog=_hdinfo.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Show hardware information'
    )
    cparser.set_defaults(func=_hdinfo)

    #
    # Command: benchmark
    #
    cparser = subparsers.add_parser(
        'benchmark',
        epilog=_benchmark.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='Run benchmark test in current machine'
    )
    cparser.add_argument('-m', '--obf-module-mode',
                         choices=Project.OBF_MODULE_MODE,
                         default=default_obf_module_mode)
    cparser.add_argument('-c', '--obf-code-mode',
                         choices=Project.OBF_CODE_MODE,
                         default=default_obf_code_mode)
    cparser.set_defaults(func=_benchmark)


    args = parser.parse_args(args)
    args.func(args)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)-8s %(message)s',
    )
    main(sys.argv[1:])
