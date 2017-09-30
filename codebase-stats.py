#!/usr/bin/env python3
import glob
import sys


try:
    import matplotlib.pyplot as plt
except:
    print('Missing library: matplotlib')
    sys.exit(0)


def generate_dist(files_dct):

    lines = list(files_dct.values())

    n, bins, patches = plt.hist(lines, bins=50,
                                facecolor='green', edgecolor='black')

    plt.xlabel('Length')
    plt.ylabel('Files')
    plt.title(r'File Length Distribution')

    plt.axis([min(lines), max(lines), 0, max(n)])
    plt.xticks(range(0, max(lines), 200))
    plt.grid(True)

    plt.show()


def collect_files():
    files_dct = {}
    files_lst = glob.glob('*.[hc]')

    for f in files_lst:
        with open(f, 'r') as h:
            data = h.readlines()
        files_dct[f] = len(data)

    return files_dct


def main():
    files_dct = collect_files()

    generate_dist(files_dct)


if __name__ == '__main__':
    main()
