# Code Analysis Tools

Includes are two python scripts to help analyze the code in a __C/C++__
codebase.

* source-probe
* codebase-stats

# Source-Probe

Uncover details about the connections between your __C/C++__ source and header files.

## Applications

This tool is useful in the following applications:

* Pruning the header includes in your source files. Usually when code is
  refactored, developers will typically forget to remove extraneous includes
  that are no longer required.
* Code refactoring. When you're refactoring code, perhaps you're looking at
  grouping together blocks of code by function. Perhaps you're unsure of how to
  group your code. Source-probe will show you what dependency a particular file
  has all other files.

The primary limitation of this script is that it does not check the
relationships of your source/header files with system headers such as `stdio.h`,
`stdlib.h`, etc.


## Installation

The main file, `source-probe.py`, is a python script that utilizes the ctags
program to generate tag information from your source files.

You will need to have the following program installed:

* [ctags](http://ctags.sourceforge.net)
* [python3](http://www.python.org)

Once installed, make sure that you have these tools available in your
environment path.


## Example

In the below example, we are running source-probe.py to analyze a header file
(cache.h) and check its relationship against all other source/header files.

```
$ source-probe.py -a cache.h -f *.[ch]

ANALYSIS: cache.h
SOURCE:             TYPE:          UTILITY (%):   USED TAGS:
update-cache.c      direct         66.7           cache_entry_size CACHE_SIGNATURE ce_size alloc_nr
read-cache.c        direct         66.7           DEFAULT_DB_ENVIRONMENT CACHE_SIGNATURE ce_size alloc_nr
init-db.c           direct         33.3           DEFAULT_DB_ENVIRONMENT DB_ENVIRONMENT
write-tree.c        direct         16.7           alloc_nr
read-tree.c         direct         16.7           DEFAULT_DB_ENVIRONMENT
commit-tree.c       direct         -
show-diff.c         direct         -
cat-file.c          direct         -
```

The list only shows files that have a relationship with cache.h. They are sorted
according to the UTILITY column, which shows you what percentage of tags
discovered inside the source file come from cache.h.

From the list of source files, you can also see that they all directly include
cache.h (i.e. they do not include cache.h from another header). Under the
USED_TAGS column, you can see what keywords or structures defined in cache.h are
being used by each source file.

# Codebase Stats

Generate a plot that shows a histogram of all the __C__ header and source files
lumped into bins dependent on the number of lines of code.

(work in progress)
