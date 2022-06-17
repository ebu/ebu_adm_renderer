Installation
============

For best results, follow this Three Step Plan to installing the EAR without
messing up your system python installation:

1) `Install Python`_
2) `Use a Virtualenv`_
3) `Install EAR`_

Install Python
--------------

EAR requires Python version 3.6+. Recent python releases include virtualenv by
default, so there's no need to install it separately.

Debian/Ubuntu
    ``sudo apt install python3``

OSX
    ``brew install python``

    OSX includes python by default, but it's often outdated and configured a
    bit strangely, so it's best to install it from homebrew.

Windows
    https://www.python.org/downloads/windows/

It will probably work with tools like anaconda, pyenv, pipenv, poetry etc., but
these are not necessary for most work, and are not actively tested.

Use a Virtualenv
----------------

A virtualenv (or `virtual environment`, or `venv`) is a self-contained python
installation, containing the interpreter and a set of libraries and programs in
a directory in your file system.

For information about how this should be used on different systems, refer to
the `official virtualenv guide
<https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/>`_.

In short, to create a virtualenv called ``env`` in the current directory:

.. code-block:: shell

    python3 -m venv env

(you may have to adjust ``python3`` to the version which you installed above)

To activate it run:

.. code-block:: shell

    source env/bin/activate

Now ``pip`` and ``python`` in this shell will operate within the virtualenv --
pip will install packages into it, and python will only see packages installed
into it. You'll have to activate the virtualenv in any other shell session
which you want to work in.

If you want to use other python tools with the EAR
(ipython, jupyter etc.) you should install and run them from the same
virtualenv.

Install EAR
-----------

To install the latest published version:

.. code-block:: shell

    pip install ear

Check that the install was successful by running ``ear-render --help`` -- you
should see the help message.

For development, or to try out the latest version, clone the repository and
install it in `editable` mode instead:

.. code-block:: shell

    git clone https://github.com/ebu/ebu_adm_renderer.git
    cd ebu_adm_renderer
    pip install -e .

Installed like this, any changes to the source will be visible without having
to re-install.

You may want to install the extra tools required for testing and development at
the same time:

.. code-block:: shell

    pip install -e .[test,dev]
