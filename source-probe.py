#!/usr/bin/env python3
import sys
import subprocess
import argparse
import os
import re
import glob
from operator import itemgetter
import textwrap
from shutil import get_terminal_size
from tempfile import NamedTemporaryFile
from shutil import copyfile


verbose_flag = False


class RetCode:
    OK, ERROR, ARGS, WARNING = range(4)


def print_error(string):
    print('\033[0;31mERROR    {}'.format(string))


def print_verbose(string):
    global verbose_flag

    if verbose_flag:
        print(string)


def bash_cmd(cmd):
    retcode = RetCode.OK

    print_verbose('Command: {}'.format(cmd))
    try:
        out_bytes = subprocess.check_output(cmd.split())
    except subprocess.CalledProcessError as e:
        out_bytes = e.output        # output generated before error
        retcode = e.returncode
    except:
        print_error('Command \'{}\' not found'.format(cmd.split()[0]))
        retcode = RetCode.ERROR

    out_text = out_bytes.decode('utf-8')

    return (out_text, retcode)


class Source:
    def __init__(self, filename):
        self.filename = filename
        self.data = ''
        self.include_lst = []
        self.tag_lst = []
        self.tag_set = set()

    def read(self):
        with open(self.filename, 'rt') as f:
            data = f.read()

        # Remove all comments
        data = re.sub(r'//.*', '', data)
        data = re.sub(r'/\*.*?\*/', '', data, flags=re.DOTALL)

        self.data = data

        includes_re = re.compile(r'#include[\s]?["<]+(?P<file>[-\w\.]+)[">]+')

        self.include_lst = includes_re.findall(self.data)

        tagname_re = re.compile(r'(\w+)\W')
        tag_set = set(tagname_re.findall(self.data + ' '))

        self.tag_lst = list(tag_set)
        self.tag_lst.sort()
        self.tag_set = set(self.tag_lst)

    def find_used_headers(self, start_lst, start_set):
        """
        Recursive function to find all the included files from the starting lst.
        """
        used_set = set([h for h in start_set if h.filename in start_lst])
        parent_set = set()

        remaining_set = start_set - used_set

        for h in used_set:
            if h.include_lst:
                parent_set |= self.find_used_headers(h.include_lst,
                                                                  remaining_set)
                remaining_set = remaining_set - parent_set

        return used_set | parent_set


    def print_utility(self, header_lst):

        header_tag_set = set()

        used_header_set = self.find_used_headers(self.include_lst,
                                                                set(header_lst))
        longest_file = 19
        for h in used_header_set:
            longest_file = max(longest_file, len(h.filename))
            header_tag_set |= h.tag_set
        longest_file += 1

        used_tag_set = header_tag_set & self.tag_set

        size = get_terminal_size((80, 20)) # fallback
        cols = max(50, size.columns - 50)

        utility_lst = []

        for h in used_header_set:
            h_tag_set = h.tag_set & used_tag_set

            if h.filename in self.include_lst:
                h_type = 'direct'
            else:
                h_type = ''

            try:
                utility = len(h_tag_set) / len(used_tag_set)
            except ZeroDivisionError as e:
                utility = 0

            istr = '\n{:<' + str(longest_file + 30) + '}'
            joiner = istr.format('')
            taglist = textwrap.fill(' '.join(h_tag_set), cols - 10)
            taglist = joiner.join(taglist.split('\n'))

            entry = {
                'filename' : h.filename,
                'type'     : h_type,
                'utility'  : utility,
                'taglist'  : taglist
            }
            utility_lst.append(entry)

        sorted_utility_lst = sorted(utility_lst, key=itemgetter('utility'),
                                                                   reverse=True)

        print('\nANALYSIS: {}'.format(self.filename))
        fstra = '{:<' + str(longest_file) + 's}{:<15s}{:<15s}{}'
        fstrn = '{:<' + str(longest_file) + 's}{:<15s}{:<15.1f}{}'
        print(fstra.format('HEADER:','TYPE:', 'UTILITY (%):','USED TAGS:'))
        for item in sorted_utility_lst:
            if item['utility'] == 0:
                f = (item['filename'], item['type'], '-', item['taglist'])
                print(fstra.format(*f))
            else:
                f = (item['filename'], item['type'], item['utility'] * 100,
                                                                item['taglist'])
                print(fstrn.format(*f))


class Header:
    def __init__(self, filename):
        self.filename = filename
        self.filetype = ''
        self.data = ''
        self.linked_tags = []
        self.include_lst = []
        self.tag_lst = []
        self.tag_set = set()

    def read(self):
        with open(self.filename, 'rt') as f:
            data = f.read()

        # Remove all comments
        data = re.sub(r'/\*.*?\*/', '', data, re.DOTALL)
        data = re.sub(r'//.*', '', data)

        self.data = data

        includes_re = re.compile(r'#include[\s]?["<]+(?P<file>[-\w\.]+)[">]+')

        self.include_lst = includes_re.findall(self.data)

    def create_tags(self):
        cur_path = os.path.abspath('.')

        abs_f = os.path.join(cur_path, self.filename)
        tag_f = NamedTemporaryFile(suffix='.tags')
        cpy_f = NamedTemporaryFile(suffix=self.filename)

        copyfile(abs_f, cpy_f.name)

        # Find externed functions/variables and convert them to prototypes so
        # that ctags can tag these to belong to the header.
        extern_func_re = re.compile(r'(extern )(.*?\))[;]{1}', re.DOTALL)
        extern_var_re  = re.compile(r'(extern )(.*?)[;]{1}', re.DOTALL)
        with open(cpy_f.name, 'r+') as f:
            data = f.read()
            data_new = extern_func_re.sub(r'\2 {}', data)
            data_new = extern_var_re.sub(r'\2;', data_new)
            f.write(data_new)

        cmd = 'ctags -f {} --excmd=number {}'.format(tag_f.name, cpy_f.name)

        (out_text, retcode) = bash_cmd(cmd)

        if retcode != RetCode.OK:
            return retcode

        with open(tag_f.name, 'rt') as f:
            data = f.read()

        ctag_lst = list(filter(lambda d: not d.startswith('!_'), \
                                                              data.split('\n')))

        valid_tag_types = (
            'define',
            'enumerator',
            'function',
            'typedef',
            'variable',
        )

        for ctag in ctag_lst:
            if ctag:
                tag = Tag(ctag)
                if tag.kind in valid_tag_types:
                    self.tag_lst.append(tag.name)

        self.tag_set = set(self.tag_lst)

    def find_used_sources(self, header_set, source_set):
        used_set = set()

        for s in source_set:
            s_header_set = s.find_used_headers(s.include_lst, header_set)

            for sh in s_header_set:
                if self.filename == sh.filename:
                    used_set.add(s)

        return used_set

    def print_utility(self, header_lst, source_lst):

        source_tag_set = set()

        used_source_set = self.find_used_sources(set(header_lst), set(source_lst))

        longest_file = 19
        for s in used_source_set:
            longest_file = max(longest_file, len(s.filename))
            source_tag_set |= s.tag_set
        longest_file += 1

        used_tag_set = source_tag_set & self.tag_set

        size = get_terminal_size((80, 20)) # fallback
        cols = max(50, size.columns - 50)

        utility_lst = []

        for s in used_source_set:
            s_tag_set = s.tag_set & used_tag_set

            if self.filename in s.include_lst:
                s_type = 'direct'
            else:
                s_type = ''

            try:
                utility = len(s_tag_set) / len(used_tag_set)
            except ZeroDivisionError as e:
                utility = 0

            istr = '\n{:<' + str(longest_file + 30) + '}'
            joiner = istr.format('')
            taglist = textwrap.fill(' '.join(s_tag_set), cols - 10)
            taglist = joiner.join(taglist.split('\n'))

            entry = {
                'filename' : s.filename,
                'type'     : s_type,
                'utility'  : utility,
                'taglist'  : taglist
            }
            utility_lst.append(entry)

        sorted_utility_lst = sorted(utility_lst, key=itemgetter('utility'),
                                                                   reverse=True)

        print('\nANALYSIS: {}'.format(self.filename))
        fstra = '{:<' + str(longest_file) + 's}{:<15s}{:<15s}{}'
        fstrn = '{:<' + str(longest_file) + 's}{:<15s}{:<15.1f}{}'
        print(fstra.format('SOURCE:','TYPE:', 'UTILITY (%):','USED TAGS:'))
        for item in sorted_utility_lst:
            if item['utility'] == 0:
                f = (item['filename'], item['type'], '-', item['taglist'])
                print(fstra.format(*f))
            else:
                f = (item['filename'], item['type'], item['utility'] * 100,
                                                                item['taglist'])
                print(fstrn.format(*f))

    def print_tag_frequency(self, header_lst, source_lst):
        tag_utility_dct = dict(zip(self.tag_lst, [0] * len(self.tag_lst)))

        used_source_set = self.find_used_sources(set(header_lst), set(source_lst))

        longest_tag_name = 19
        for tag in tag_utility_dct.keys():
            for s in used_source_set:
                if tag in s.tag_set:
                    tag_utility_dct[tag] += 1
            longest_tag_name = max(longest_tag_name, len(tag))
        longest_tag_name += 1

        print('\nTAG USAGE FREQUENCY: {}'.format(self.filename))

        sorted_tag_utility_lst = sorted(tag_utility_dct.items(),
                                                key=itemgetter(1), reverse=True)
        fstra = '{:<' + str(longest_tag_name) + '}{}'
        fstrn = '{:<' + str(longest_tag_name) + '}{}'
        for tag,cnt in sorted_tag_utility_lst:
            if cnt == 0:
                print(fstra.format(tag, '-'))
            else:
                print(fstrn.format(tag, cnt))


class Tag:
    def __init__(self, ctag):
        self.ctag = ctag
        self.name = None
        self.path = None
        self.file = None
        self.addr = None
        self.kind = None

        self.parse_ctag(ctag)

    #
    #    http://ctags.sourceforge.net/FORMAT
    #
    def parse_ctag(self, ctag):
        try:
            name, file, addr, kind = ctag.split('\t')[0:4]
            file_parts = file.split(os.path.sep)

            self.name = name
            self.file = file_parts[-1]
            self.path = os.path.sep.join(file_parts[0:-1])
            self.addr = addr.rstrip(';"')

            if kind is 'c':
                self.kind = 'class'     # class name
            elif kind is 'd':
                self.kind = 'define'    # define from #define XXX
            elif kind is 'e':
                self.kind = 'enumerator'
            elif kind is 'f':
                self.kind = 'function'  # function or method name
            elif kind is 'F':
                self.kind = 'file'      # file name
            elif kind is 'g':
                self.kind = 'enum_name'
            elif kind is 'm':
                self.kind = 'member'    # member of structure or class data
            elif kind is 'p':
                self.kind = 'prototype' # function prototype
            elif kind is 's':
                self.kind = 'struct_tag'
            elif kind is 't':
                self.kind = 'typedef'
            elif kind is 'u':
                self.kind = 'union'     # union name
            elif kind is 'v':
                self.kind = 'variable'
            else:
                self.kind = ''
                print_error('Unknown kind: {}'.format(kind))

        except ValueError:
            print('Unable to parse:   {}'.format(ctag))
            return


def filter_files(ext_tpl, file_lst, exclude_file_lst, recurse=False):
    '''
    Find all the source/header files in the current directory. Return a
    sorted list of all the found files.
    '''
    file_set = set()
    exclude_lst = []

    if exclude_file_lst:
        filtered_exclude_lst = list(filter(lambda d: d.endswith(ext_tpl),
                                                              exclude_file_lst))
        for x in filtered_exclude_lst:
            exclude_lst.extend(glob.glob(x))
            print_verbose('Excluded: {}'.format(x))

    if recurse:
        for relpath, dirs, files in os.walk('.'):
            for f in files:
                full_path = os.path.join(relpath, f).lstrip('./\\')
                if full_path.endswith(ext_tpl) and full_path not in exclude_lst:
                    file_set.add(full_path)
    else:
        if file_lst:
            # Use the files passed in as arguments
            fi = filter(lambda d: d.endswith(ext_tpl) and d not in exclude_lst,
                        file_lst)
            file_set = set(fi)

    filtered_file_lst = list(file_set)
    filtered_file_lst.sort()

    return filtered_file_lst


def parse_arguments():
    parser = argparse.ArgumentParser(
                                description='Analyze header file relationships')

    parser.add_argument('-a', '--analyze',
        dest='analysis_lst',
        metavar='file',
        nargs='+',
        help='subset of source and/or header files to analyze. This is the ' \
             'analysis set.')

    parser.add_argument('-f', '--files',
        dest='file_lst',
        metavar='file',
        nargs='+',
        help='all source and header files used for analysis for the ' \
             'analysis set')

    parser.add_argument('-v', '--verbose',
        dest='verbose',
        action='store_true',
        help='verbose mode')

    parser.add_argument('-t', '--tag-frequency',
        dest='show_tag_freq',
        action='store_true',
        help='show utility at the tag level')

    parser.add_argument('-r', '--recursive',
        dest='recursive',
        action='store_true',
        help='recursive scan for files')

    parser.add_argument('-e', '--exclude',
        dest='exclude_lst',
        metavar='file',
        nargs='*',
        help='files to ignore')

    return parser.parse_args()


def main():
    global verbose_flag

    args = parse_arguments()
    verbose_flag = args.verbose

    if not args.analysis_lst:
        print('Specify files to analyze using the \'-a\' argument')
        return RetCode.ARGS

    if not args.file_lst:
        print('Specify all source/header files using the \'-f\' argument')
        return RetCode.ARGS


    analysis_file_lst = list(set(args.analysis_lst))
    full_file_lst = list(set(args.file_lst) | set(args.analysis_lst))

    h_files = filter_files(('.h'), full_file_lst, args.exclude_lst,
                           args.recursive)
    c_files = filter_files(('.c'), full_file_lst, args.exclude_lst,
                           args.recursive)

    cpp_files = filter_files(('.cpp'), full_file_lst, args.exclude_lst,
                           args.recursive)

    c_files.extend(cpp_files)

    if not h_files:
        print_error('No header files specified.')
        return RetCode.ERROR

    if not c_files:
        print_error('No source files specified.')
        return RetCode.ERROR

    sources = []
    headers = []
    analysis_files = []

    for c in c_files:
        cf = Source(c)
        cf.read()
        sources.append(cf)

        if c in analysis_file_lst:
            analysis_files.append(cf)

    for h in h_files:
        hf = Header(h)

        try:
            hf.read()
            hf.create_tags()
        except Exception as e:
            print_error(e)
            return RetCode.ERROR

        headers.append(hf)

        if h in analysis_file_lst:
            analysis_files.append(hf)

    for af in analysis_files:
        if isinstance(af, Source):
            af.print_utility(headers)

        elif isinstance(af, Header):
            af.print_utility(headers, sources)
            if args.show_tag_freq:
                af.print_tag_frequency(headers, sources)

    return RetCode.OK


if __name__ == '__main__':
    try:
        retcode = main()
        sys.exit(retcode)
    except KeyboardInterrupt as e:
        print('\nAborting')
