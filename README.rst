Mobilevids Downloader
=====================

.. raw:: html

   <!-- TOC -->

-  `Introduction <#introduction>`__
-  `Features <#features>`__
-  `Installation instructions <#installation-instructions>`__

   -  `Recommended installation method for all Operating
      Systems <#recommended-installation-method-for-all-operating-systems>`__

-  `Filing an issue/Reporting a bug <#filing-an-issuereporting-a-bug>`__
-  `Contact <#contact>`__

.. raw:: html

   <!-- /TOC -->

Introduction
============

`Mobilevids <https://www.mobilevids.org>`__ is an amazing website for
downloading movies and tv shows.

This script makes it easier to batch download movies or TV serials.

Why is this helpful? A utility like
`wget <https://sourceforge.net/projects/gnuwin32/files/wget/1.11.4-1/wget-1.11.4-1-setup.exe>`__
can work, but has the following limitations:

1. Video names have numbers in them, but this does not correspond to the
   actual order. Manually renaming them is a pain that is best left for
   computers.
2. Using names from the syllabus page provides more informative names.
3. Using ``wget`` in a for loop picks up extra videos which are not
   posted/linked, and these are sometimes duplicates.

This work was originally inspired in part by
`coursera-dl <https://www.github.com/coursera-dl/coursera-dl>`__.

Features
========

-  Support for all kinds of movies / TV shows.
-  Intentionally detailed names, so that it will display and sort
   properly on most interfaces (e.g.,
   `VLC <https://f-droid.org/repository/browse/?fdid=org.videolan.vlc>`__
   or MX Video on Android devices).
-  Login credentials accepted on command-line or from ``.netrc`` file.
-  Core functionality tested on Linux, Mac and Windows.

Installation instructions
=========================

``mobilevids-dl`` requires Python 3 and a free Mobilevids account.

**Note:** We *strongly* recommend that you use a Python 3 interpreter
(3.9 or later).

On any operating system, ensure that the Python executable location is
added to your ``PATH`` environment variable and, once you have the
dependencies installed (see next section), for a *basic* usage, you will
need to invoke the script from the main directory of the project and
prepend it with the word ``python``. You can also use more advanced
features of the program by looking at the “Running the script” section
of this document.

Recommended installation method for all Operating Systems
---------------------------------------------------------

From a command line (preferably, from a virtual environment), simply
issue the command:

::

   pip install mobilevids-dl

This will download `the latest released
version <https://pypi.python.org/pypi/mobilevids-dl>`__ of the program
from the `Python Package Index (PyPI) <https://pypi.python.org/>`__
along with *all* the necessary dependencies. At this point, you should
be ready to start using it.

If this does not work, because your Python 2 version is too old
(e.g. 2.7.5 on Ubuntu 14.4), try:

::

   apt-get install python3 python3-pip
   pip3 install mobilevids-dl

instead.

**Note 1:** We strongly recommend that you *don’t* install the package
globally on your machine (i.e., with root/administrator privileges), as
the installed modules may conflict with other Python applications that
you have installed in your system (or they can interfere with
``mobilevids-dl``). Prefer to use the option ``--user`` to
``pip install``, if you need can.

**Note 2:** As already mentioned, we *strongly* recommend that you use a
new Python 3 interpreter (e.g., 3.9 or later), since Python 3 has better
support for SSL/TLS (for secure connections) than earlier versions. If
you must use Python 2, be sure that you have at least Python 2.7.9
(later versions are OK). Otherwise, you can still use ``mobilevids-dl``,
but you will have to install the extra package ``ndg-httpsclient``,
which may involve compilation (at least on Linux systems).

Running the script
==================

Refer to ``mobilevids-dl --help`` for a complete, up-to-date reference
on the runtime options supported by this utility.

.. code:: bash

   usage: mobilevids_dl [-h] [-a] [-d] [-i] [-e EPISODE] [-m MOVIE] [-s SEASON] [-t TV] [search]

   Mobilevids Downloader script

   positional arguments:
     search

   optional arguments:
     -h, --help            show this help message and exit
     -a, --ascii           show ascii art
     -d, --debug           debugs the program - duh
     -i, --info            show info about movie/show
     -e EPISODE, --episode EPISODE
                           download a single episode (must be used with -t [TV ID] and -s [SEASON]
     -m MOVIE, --movie MOVIE
                           downloads the ID of a movie
     -s SEASON, --season SEASON
                           specify season to download (must use with -t)
     -t TV, --tv TV        download a TV show based on it's ID

Run the script to download the media by providing your Mobilevids
account credentials (e.g. email address and password or a ``~/.netrc``
file), the movie name, as well as any additional parameters:

On \*nix platforms, the use of a ``~/.netrc`` file is a good alternative
to specifying both your username (i.e., your email address) and password
every time on the command line. To use it, simply add a line like the
one below to a file named ``.netrc`` in your home directory (or the
`equivalent <http://stackoverflow.com/a/6031266/962311>`__, if you are
using Windows) with contents like:

::

       machine mobilevids-dl login <user> password <pass>

Create the file if it doesn’t exist yet. From then on, you can switch
from using ``-u`` and ``-p`` to simply call ``mobilevids-dl`` with the
option ``-n`` instead. This is especially convenient, as typing
usernames (email addresses) and passwords directly on the command line
can get tiresome (even more if you happened to choose a “strong”
password).

Reporting issues
================

Before reporting any issue please follow the steps below:

1. Verify that you are running the latest version of the script, and the
   recommended versions of its dependencies, see them in the file
   ``requirements.txt``. Use the following command if in doubt:

   ::

       pip install --upgrade mobilevids-dl

2. If the problem persists, feel free to `open an
   issue <https://github.com/ahron-maslin/mobilevids-dl/issues>`__ in
   our bugtracker, please fill the issue template with *as much
   information as possible*.

Filing an issue/Reporting a bug
===============================

When reporting bugs against ``mobilevids_dl``, please don’t forget to
include enough information so that you can help us help you:

-  Is the problem happening with the latest version of the script?
-  What operating system are you using?
-  Do you have all the recommended versions of the modules? See them in
   the file ``requirements.txt``.
-  What are the precise messages that you get? Please, use the
   ``--debug`` option before posting the messages as a bug report.
   Please, copy and paste them. Don’t reword/paraphrase the messages.

Contact
=======

Please, post bugs and issues on [github][11]. Please, **DON’T** send
support requests privately to the maintainers! We are quite swamped with
day-to-day activities. If you have problems, **PLEASE**, file them on
the issue tracker.
