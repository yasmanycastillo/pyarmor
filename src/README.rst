Pyarmor
=======

Pyarmor is a command line tool used to import or run obfuscated python
scripts. Only by a few extra files, pyarmor can run and imported
obfuscated files in the normal python environments.

Pyarmor just likes an enhancement which let python could run or import
obfuscated files.

Main Features
-------------

- Run obfuscated script or import obfuscated module
- Expire obfuscated files
- Bind obfuscated files to harddisk, mac address, ip address etc.

Support Platforms
-----------------

- Python 2.5, 2.6, 2.7 and Python3

- Prebuilt Platform: win32, win_amd64, linux_i386, linux_x86_64, darwin_x86_64

- Embeded Platform: Raspberry Pi, Banana Pi, ts-4600

Installation
------------

Got source package from `pypi/pyarmor <https://pypi.python.org/pypi/pyarmor>`_

Pyarmor is a command line tool, main script is pyarmor.py. After you
got source package, unpack it to any path, then run paramor.py as
common python script

    python pyarmor.py

Basic Usage
-----------

The following examples show how to obfuscate a python package
**pybench**, which locates in the **examples/pybench** in the source
of pyarmor.

Obfuscate package **pybench**::

    python pyarmor.py obfuscate --src examples/pybench --entry pybench.py \
                                "*.py" "package/*.py"

    # Note that quotation mark is required for file patterns, otherwise
    # it will be expanded base on current path by shell.
    #
    # This command will create a extra file .pyarmor_capsule.zip in the
    # --src path, and save all the obfuscated scripts to default output
    # path "dist" in the current path
    #
    cd dist

    # Check obfuscated script
    cat pybench.py

    # Run obfuscated script
    python pybench.py

Use project to manage obfuscated scripts::

    mkdir projects
    python pyarmor.py init --src examples/pybench --entry pybench.py \
                           projects/pybench

    # This command will create 2 files: .pyarmor_config, .pyarmor_capsule.zip
    # in the project path "projects/pybench"
    cd projects/pybench

    # And there is a shell script "pyarmor" is created at the same time.
    # (In windows, the name is "pyarmor.bat")
    #
    # Now run "pyarmor" to obfuscated all the scripts by subcommand "build"
    #
    ./pyarmor build

    # Check obfuscated script
    cd dist
    cat pybench.py

    # Run obfuscated script
    python pybench.py

Start a webui to manage project::

    # For windows
    webui/manager.bat

    # For linux
    webui/manager.sh

Here is online demo `Pyarmor Demo <http://pyarmor.dashingsoft.com>`_

More usage, refer to **user-guide.md** in the source package

For more information, refer to `Pyarmor Homepage <https://github.com/dashingsoft/pyarmor>`_
