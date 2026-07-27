# Mobilevids Downloader


<!-- TOC -->

- [Introduction](#introduction)
- [Features](#features)
- [Installation instructions](#installation-instructions)
    - [Recommended installation method for all Operating Systems](#recommended-installation-method-for-all-operating-systems)
- [Filing an issue/Reporting a bug](#filing-an-issuereporting-a-bug)
- [Contact](#contact)

<!-- /TOC -->

# Introduction

[Mobilevids][1] is an amazing website for downloading movies and tv shows.

This script makes it easier to batch download movies or TV serials.

Why is this helpful?  A utility like [wget][2] can work, but has the
following limitations:

1. Video names have numbers in them, but this does not correspond to
    the actual order.  Manually renaming them is a pain that is best left
    for computers.
2. Using names from the syllabus page provides more informative names.
3. Using `wget` in a for loop picks up extra videos which are not
    posted/linked, and these are sometimes duplicates.

This work was originally inspired in part by [coursera-dl][3].


# Features
  * Support for all kinds of movies / TV shows.
  * Intentionally detailed names, so that it will display and sort properly
    on most interfaces (e.g., [VLC][4] or MX Video on Android devices).
  * Login credentials accepted on command-line or from `.netrc` file.
  * Core functionality tested on Linux, Mac and Windows.


# Installation instructions

`mobilevids-dl` requires Python 3.10+ and a free Mobilevids account.

On any operating system, ensure that the Python executable location is added
to your `PATH` environment variable and, once you have the dependencies
installed (see next section), for a *basic* usage, you will need to invoke
the script from the main directory of the project and prepend it with the
word `python`.  You can also use more advanced features of the program by
looking at the "Running the script" section of this document.


## Recommended installation method for all Operating Systems

From a command line (preferably, from a virtual environment), simply issue
the command:

    pip install mobilevids-dl


This will download [the latest released version][7] of the program from the
[Python Package Index (PyPI)][6] along with *all* the necessary
dependencies. At this point, you should be ready to start using it.

**Note:** We strongly recommend that you *don't* install the package
globally on your machine (i.e., with root/administrator privileges), as the
installed modules may conflict with other Python applications that you have
installed in your system (or they can interfere with `mobilevids-dl`). Prefer
to install it into a virtual environment, or use `pip install --user`.


# Running the script

Refer to `mobilevids-dl --help` for a complete, up-to-date reference on the runtime options
supported by this utility.

```bash
usage: mobilevids-dl [-h] [--version] [-a] [-d] [-i] [-e EPISODE] [-m MOVIE]
                     [-n [PATH]] [-o DIR] [-p PASSWORD] [--segments SEGMENTS]
                     [-s SEASON] [-t TV] [-u USERNAME]
                     [search]

Mobilevids Downloader script

positional arguments:
  search                title to search for

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -a, --ascii           show ascii art
  -d, --debug           enable debug logging
  -i, --info            show info about movie/show
  -e EPISODE, --episode EPISODE
                        download a single episode (requires -t [TV ID] and -s
                        [SEASON])
  -m MOVIE, --movie MOVIE
                        ID of a movie to download
  -n [PATH], --netrc [PATH]
                        read credentials from a netrc file, using the default
                        location if PATH is omitted
  -o DIR, --output DIR  directory to save downloads in (default: ~/downloads)
  -p PASSWORD, --password PASSWORD
                        Mobilevids password
  --segments SEGMENTS   parallel connections per download (default: 4)
  -s SEASON, --season SEASON
                        season to download (requires -t)
  -t TV, --tv TV        ID of a TV show to download
  -u USERNAME, --username USERNAME
                        Mobilevids username
```

Credentials are resolved in this order:

1. the `--username`/`--password` command-line flags
2. the `MOBILEVIDS_USERNAME` and `MOBILEVIDS_PASSWORD` environment variables
3. a `.netrc` file

The environment variables are the recommended option: command-line arguments
are visible to other users on the same machine (via the process list) and get
saved in your shell history.

On \*nix platforms, a `~/.netrc` file is a good alternative to typing your
username and password every time. To use it, add an entry like the one below
to a file named `.netrc` in your home directory (or the [equivalent][5], if
you are using Windows):
```
machine mobilevids
    login <user>
    password <pass>
```
Create the file if it doesn't exist yet, and make sure only you can read it
(`chmod 600 ~/.netrc`). From then on, you can switch from `-u`/`-p` to simply
calling `mobilevids-dl`.

# Reporting issues

Before reporting any issue please follow the steps below:

1. Verify that you are running the latest version of the script, and the
recommended versions of its dependencies, see them in the file
`requirements.txt`.  Use the following command if in doubt:

        pip install --upgrade mobilevids-dl

2. If the problem persists, feel free to [open an issue][issue] in our
bugtracker, please fill the issue template with *as much information as
possible*.

[issue]: https://github.com/ahron-maslin/mobilevids-dl/issues

# Filing an issue/Reporting a bug

When reporting bugs against `mobilevids-dl`, please don't forget to include
enough information so that you can help us help you:

* Is the problem happening with the latest version of the script?
* What operating system are you using?
* Do you have all the recommended versions of the modules? See them in the
  file `requirements.txt`.
* What are the precise messages that you get? Please run with `--debug` and
  copy and paste the output rather than paraphrasing it. Your password is
  never printed, but review the output before posting in case it contains
  anything else you'd rather not share (e.g. video titles or IDs).

# Contact

Please, post bugs and issues on [github][7]. Please, **DON'T** send support
requests privately to the maintainers! We are quite swamped with day-to-day
activities. If you have problems, **PLEASE**, file them on the issue tracker.

[1]: https://www.mobilevids.org
[2]: https://sourceforge.net/projects/gnuwin32/files/wget/1.11.4-1/wget-1.11.4-1-setup.exe
[3]: https://www.github.com/coursera-dl/coursera-dl
[4]: https://f-droid.org/repository/browse/?fdid=org.videolan.vlc
[5]: http://stackoverflow.com/a/6031266/962311
[6]: https://pypi.python.org/
[7]: https://pypi.python.org/pypi/mobilevids-dl
