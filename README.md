
Main/dev:
[![Documentation Status](https://readthedocs.org/projects/pynastran-git/badge/?version=latest)](http://pynastran-git.readthedocs.io/en/latest/?badge=latest)
[![Linux Status](https://github.com/SteveDoyle2/pyNastran/workflows/CI/badge.svg)](https://github.com/SteveDoyle2/pyNastran/actions?query=workflow%3ACI+branch%3Amaster)
[![Coverage Status](https://codecov.io/gh/SteveDoyle2/pyNastran/branch/main/graph/badge.svg)](https://codecov.io/gh/SteveDoyle2/pyNastran)
[![Discord](https://img.shields.io/badge/help_forum-discourse-blue.svg)](https://discord.gg/s8RfSkZDHA)

See the  [Installation Instructions](https://pynastran-git.readthedocs.io/en/1.3/installation/installation.html#installation-from-release)
for instructions on installing pyNastran.


<!---
.. |DiscourseBadge| image:: https://img.shields.io/badge/help_forum-discourse-blue.svg
.. _DiscourseBadge: https://discourse.matplotlib.org
--->

### v1.3.4

[Download GUI](https://sourceforge.net/projects/pynastran/files/?source=navbar) (latest is from 2022/5/30)

Also, check out the:
  * [![PyPi Version](https://img.shields.io/pypi/v/pynastran.svg)](https://pypi.python.org/pypi/pyNastran)
  * [Discussion forum](http://groups.google.com/group/pynastran-discuss) (intended for questions about the latest release)
  * [Developer forum](http://groups.google.com/group/pynastran-dev) (intended for questions about the main branch)
  * [Docs](https://pynastran-git.readthedocs.io/en/1.3/)
  * [Code of Conduct](https://github.com/SteveDoyle2/pyNastran/blob/main/code_of_conduct.md)
  * [Contributing](https://github.com/SteveDoyle2/pyNastran/blob/main/contributing.rst)

for more detailed information.

### Blogs
  * [Flutter Analysis in pyNastran](https://www.m4-engineering.com/flutter-analysis-with-pynastran/)


### Code of Conduct

Everyone interacting in the setuptools project’s codebase, issue trackers, chat room/Discord, and mailing lists is expected to follow the [Code of Conduct](https://github.com/SteveDoyle2/pyNastran/blob/main/code_of_conduct.md).


<!---
[![Windows Status](https://ci.appveyor.com/api/projects/status/1qau107h43mbgghi/branch/main?svg=true)](https://ci.appveyor.com/project/SteveDoyle2/pynastran)
[![codecov](https://codecov.io/gh/SteveDoyle2/pyNastran/branch/main/graph/badge.svg)](https://codecov.io/gh/SteveDoyle2/pyNastran)
[![Coverage Status](https://img.shields.io/coveralls/SteveDoyle2/pyNastran/main.svg)](https://coveralls.io/github/SteveDoyle2/pyNastran?branch=main)
--->

<!---
[![Build status](https://ci.appveyor.com/api/projects/status/1qau107h43mbgghi/branch/main?svg=true)](https://ci.appveyor.com/project/SteveDoyle2/pynastran/branch/main)
[![Build status](https://ci.appveyor.com/api/projects/status/1qau107h43mbgghi?svg=true)](https://ci.appveyor.com/project/SteveDoyle2/pynastran)
[![Build Status](https://travis-ci.org/SteveDoyle2/pyNastran.png)](https://travis-ci.org/SteveDoyle2/pyNastran)
[![Coverage Status](https://coveralls.io/repos/github/SteveDoyle2/pyNastran/badge.svg?branch=main)](https://coveralls.io/github/SteveDoyle2/pyNastran?branch=main)
[![Requirements Status](https://img.shields.io/requires/github/SteveDoyle2/pyNastran/main.svg)](https://requires.io/github/SteveDoyle2/pyNastran/requirements/?branch=main)	|
### v1.4

Last year MSC provided a copy of MSC Nastran free of charge to help support the project.
Since then, modern MSC Nastran support has been added.
In addition, NX 64-bit and OptiStruct support has been improved.

The biggest new features are:
 - MSC 2020 support (including contact)
 - much improved 64 bit support
 - improved op2 support

Programmatics:
 - Supports Python 3.7 - 3.10 (later versions of Python requires downloading from github)
 - GUI is compatible with PyQt5/6 and PySide2/6 and VTK 7-10
 - improved testing of old versions of packages
 - updated nptyping requirements

BDF:
 - fixed CAERO1 paneling bug
 - 8 new cards: BGSET, BGADD, BCTPARM, BCBODY, TOPVAR, MATEV, PCOMPLS, TABDMP1

OP2:
 - 20 new results
 - vectorized op2 writing

GUI:
 - transient/complex fringe only animations now supported

See pyNastran `v1.4.0 release notes <https://github.com/SteveDoyle2/pyNastran/releases/tag/v1.4.0>`_ for details on the other changes.


--->

# Overview

pyNastran is an interface library to the various Nastran file formats (BDF, OP2, OP4).
Using the BDF interface, you can read/edit/write Nastran geometry without worrying about
field formatting.  Many checks are also performed to verify that your model is correct.
Using the OP2 interface, you can read large result files quickly and efficiently.
Additionally, you can also extract a subset of the result data and write OP2/F06 result
files.  For a more detailed list of features, see:
  * [Features](https://pynastran-git.readthedocs.io/en/1.3/quick_start/features.html#overview)

Using the pyNastran GUI, you can read in Nastran models and quickly view results for a model.
While it's no FEMAP/Patran, it can replace many tasks that would otherwise require a
commercial program.

![GUI](https://github.com/SteveDoyle2/pynastran/blob/main/pyNastran/gui/images/caero.png)


# News

<!---

This should be hidden...
--->

### v1.3.4 has been released (2022/5/30)
This is a a bug fix release mainly to address dependency changes:

Programmatics:
 - supports Python 3.7-3.10
 - support for nptyping 1.1.1-2.0 (removed as a required dependency)
 - support for h5py >3.0
 - GUI is compatible with PyQt5/6 and PySide2/6 and VTK 7-10

There are also at least 33 bugs fixed and a few features added from the 1.4 release (e.g., pathlib support, subcase limiting in the flutter F06 parser).

See pyNastran `v1.3.4 release notes <https://github.com/SteveDoyle2/pyNastran/releases/tag/v1.3.4>`_ for details on the other changes.


### v1.3.3 (2020/6/28)

This is a bug fix only release outside of:
      ```python
     >>> subcase.add_set_from_values(set_id, values)
     ```

which was overly complicated to do before.

Programmatics:
 - Supports Python 3.7 and 3.8
 - GUI is compatible with PyQt5 and PySide2 and VTK 7-9
 - improved testing of old versions of packages
 - updated nptyping requirements
 - support for NX 2019.0, 2019.1

See pyNastran `v1.3.3 release notes <https://github.com/SteveDoyle2/pyNastran/releases/tag/v1.3.3>`_ for details on the 54 bug fixes.  Not too bad for 2.5 months!


### pyNastran v1.3.2 has been released (2020/4/8)

With Python 2 now officially dead, it's time for a new killer feature to get the last few people to switch.

There is now support for writing OP2 files!  They're difficult to create from scratch,
but modifying an existing one isn't difficult.  This includes geometry support.

In addition, many new OP2 results have been added.  Modern NX Nastran should work much better.

Programmatics:
 - Supports Python 3.7 and 3.8
 - Dropping Python 2.7 and 3.6 support
 - GUI is compatible with PyQt5 and PySide2
 - improved testing of old versions of packages

BDF:
 - enhancements
   - 405 cards supported (up from 373)
   - improved mesh utilities
      - bdf mirror, bdf convert, bdf export_caero_mesh
      - additional `bdf scale`, which takes arbitrary mass, length, time, pressure, or velocity scale factors (3 of 5) to apply a scaling law
   - added deck guessing with punch=None

OP2:
 - enhancements:
   - OP2 write support
   - fixed most pandas deprecation warnings/added support for pandas 0.25
   - much improved NX 2019.2 support
 - minor enhancements:
   - more hdf5 results
   - a few more cards supported in the OP2 geometry reader
   - preliminary NX 64-bit support
   - more MSC versions supported
   - sped up R1TABRG (optimization) reading
   - various geometry cards added
   - supports more PARAM reading
 - new results:
    - composite failure indices (OEFIT)
    - sensitivity support (DSCMCOL)
    - Cambpell diagrams (CDDATA)
    - eigenvectors (BOPHIGF)
    - grid point forces SORT2 (OGPFB2)
    - stress/strain/force
      - random stress/strain (OESVM1/2, OESVM1C, OSTRVM1/2, OSTRVM2, OESXRM1C, OESXNO1, OESXNO1C)
      - real/complex stress/strain/force output for centroidal CQUADR/CTRIAR
      - complex CBEAR forces
      - real CFAST, CWELD forces
      - nonlinear cbush stress/strain/force
    - other
      - PSDs
      - optimization
        - convergence table
        - design variables
        - weight, displacement, stress, strain, force, composite stress, composite strain, fractional mass response
    - SOL 401/402 results:
      - eigenvalue_fluid (LAMAF, LAMAS)
      - eigenvectors (BOPHIGF, BOPHIGS)
      - temperature (OTEMP1)
      - solution set
        - results: displacement, velocity, acceleration, eigenvectors:
        - tables: OUXY1, OUXY2, OPHSA

GUI:
 - enhancements:
   - partial custom results many now be loaded
   - animation now supports complex fringe
   - result case description now shows the mode/time/frequency
   - result case description now shows the min/max value as well as the location
   - map centroidal to nodal option
   - adding node/element highlight menu
   - adding node/element mark/label menu
   - result case description now shows the min/max value as well as the location
   - result case description now shows the mode/time/frequency
 - minor enhancements:
   - added export result option to right-click menu
   - more keyboard shortcuts
 - nastran:
   - geometry:
     - added preferences for geometry/results to speed up model loading
     - element & material coordinate systems
   - results
     - added acoustic displacements (OUG1F)
     - real/complex stress/strain/force results
       - plate by upper/lower, composite plates by ply, bars, rods, springs, cbush, cdamp
     - fractional mass response

F06:
 - KE support for plot_145

Many bug fixes, and a few more details on features, can be found in the ![Release Notes](https://github.com/SteveDoyle2/pyNastran/blob/1.3/releaseNotes.md)

### v1.3.1/v1.3.0 (2020/4/8)

This result has been superseded by 1.3.2.  The PyPi page was fixed.

### v1.2.1 (2019/5/24)

I keep saying to myself there's not much to add, but Nastran is huge.  Beyond HDF5
support in the BDF, I'm a huge fan of the new ability to keep track of which include file a
card came from and write it as a separate file.  It's limited in usefulness, but very handy
in certain cases.  There's a new (still preliminary) superelement capability.  I'm far
from a superelement expert, but it's probably useful.

The OP2 reader now supports SORT2 along with much improved random results reading.
If you're using 60+ GB OP2s, you probably have had issues with RAM usage in the past.
With the new ability to dump the OP2 directly to HDF5, this should not be an as much of
an issue.  It's not 100% implemented, so let me know if you need it for another result.

Regarding the GUI, there are also some new features.  Groups work a bit better, but aren't
quite perfect.  Logging has been dramatically sped up, so the GUI loads faster, and you can
load Nastran models even faster if you disable additional results (e.g., element quality).

Finally, Python 2.7 is end of life.  Numpy, scipy, and matplotlib have all dropped
Python 2.7 support.  It's time for pyNastran to as well.  The OP2 reader is 30% faster in
Python 3.6+ than Python 2.7, so it's not all bad!

Programmatics:
 - This is the last Python 2.7 release.
 - Dropping Python 3.5 support
 - Supports Python 2.7, 3.6-3.7
 - GUI is compatible with PyQt4/PyQt5 as well as PySide/PySide2
 - improved testing of old versions of packages

BDF:
 - 373 cards supported (up from 343)
 - added abiltity to write models to separate include files
     ```python
     >>> model = BDF()
     >>> model.read_bdf(bdf_filename, save_file_structure=True)

     out_filenames = {
         bdf_filename : bdf_filename_new,
         include_filename : include_filename_new,
     }
     >>> model.write_bdfs(out_filenames, relative_dirname=None, is_windows=None)
     >>> ifile = model.grids[1].ifile
     ```

 - HDF5 import/export
      ```python
     >>> model = read_bdf(bdf_filename)
     >>> model.export_hdf5_filename(hdf5_filename)
     >>> model_new = OP2()
     >>> model_new.load_hdf5_filename(hdf5_filename)
     ```

 - preliminary superelement support
     ```python
     >>> model.read_bdf(bdf_filename)
     >>> model.superelement_models[1].nodes
     ```


OP2:
 - reorganization of random op2 results into op2.results.psd (or ato, no, crm, rms) to aid in finding data
 - reorganization of op2 class to reduce number of functions in the object.  This affects any custom table reading.
 - improved optimization response reading
 - limited SORT2 support
 - fixed CD transformation bug for BOUGV1 and BOPHIG1 tables
 - Improved HDF5 export/import support (e.g., matrices, random results)

 - Can optionally save directly to HDF5 instead of numpy (limited).
 - Loading OP2s to an HDF5 file to decrease memory usage
      ```python
     >>> op2_model = OP2()
     >>> op2_model.load_as_h5 = True
     >>> op2_model.read_op2(op2_filename)
     ```

OP2Geom:
 - HDF5 support
 - reading EQEXIN/S, GPT, GPDT, CSTM/S tables (recovery of nodes & coordinate with OP2Geom)
 - fixed theta/mcid reading for CTRIA3/CQUAD4
 - fixed CQUAD8 bug

GUI:
 - sped up HTML logging
 - much improved groups menu
 - options for Nastran in preferences menu to speed up loading/limit memory usage
 - pyNastran BDF pickle reading
 - pyNastran OP2 HDF5 reading (not MSC's format)
 - visualization when pickling nodes/elements
 - min/max labels
 - highlight menu
 - Patran-style colors
 - custom force vectors
 - AVL support


Known issues:
 - Transient Pandas Dataframes will fail for newer versions of numpy/pandas.
   If anyone knows how to use a MultiIndex, this is probably pretty easy to fix.

### v1.2.0 (2019/5/21)

This result has been superseded by 1.2.1.  See release notes for details.

### v1.1.0 (2018/6/26)

|  Version  | Docs  | Status |
| :--- 	  | :--- 	  | :--- 	  |
|  [![PyPi Version](https://img.shields.io/pypi/v/pynastran.svg)](https://pypi.python.org/pypi/pyNastran) |  |  [![Coverage Status](https://img.shields.io/coveralls/SteveDoyle2/pyNastran/v1.1.svg)](https://coveralls.io/github/SteveDoyle2/pyNastran?branch=v1.1) |

It's been roughly a year and ~100 tickets closed since the last version, so it's probably
time for another release!  I want to thank everybody who helped with this release, especially
Michael Redmond.  He is working on h5Nastran, which ties in with pyNastran.  It's not quite
ready yet, but it offers the possibility of major speedups for large models.

Regarding features, the focus has again been on robustness and testing.  There has been
a 10% increase in the testing coverage (the same as v0.8 to v1.0).  There are a few
changes (mainly in the BDF) though.  The GUI now also supports PyQt4, PyQt5, and Pyside
with the same API, so it's a bit easier to install from source as simplifying licensing
issues as PyQt is GPL.

Programmatics:
 - Dropping Python 3.4 support
 - Supports Python 2.7, 3.5-3.6
 - dropping VTK 5/6 support for the GUI

BDF:
 - 343 cards supported (up from 312)
 - cross-referencing is now more straightforward to new users (much of v1.0 works using the `_ref` option)
   - ``*_ref`` attributes are cross-referenced
      - ``element.nodes`` is not cross-referenced
      - ``element.nodes_ref`` is cross-referenced
 - pickling to reload your deck ~5x faster
 - decreased time required for Case Control Deck with large SETs, and many load cases
 - improved optimization checks

OP2:
 - HDF5 export/import support
      ```python
     >>> op2_model = read_op2(op2_filename)
     >>> op2_model.export_hdf5_filename(hdf5_filename)
     >>> op2_model_new = OP2()
     >>> op2_model_new.load_hdf5_filename(hdf5_filename, combine=True)
     ```
 - pandas support for matrices
 - couple more results vectorized (e.g., complex strain energy, DMIG strain energy, some forces)
 - grid_point_stresses supported (disabled since v0.7)
 - fixed sparse matrices being stored as dense matrices

GUI:
 - preliminary support for PySide
 - can now mix and match fringe/displacement/vector results (e.g., max principal stress shown on a displaced model)
 - improved animation menu
    - in gui animation
    - more animation profiles
 - bar profile visualization
 - nominal geometry (useful for deflection plots)
 - improved optimization support
 - improved picking display
 - better PSHELL/PCOMP distinction

Known issues:
 - Transient Pandas Dataframes will fail for newer versions of numpy/pandas.

### v1.0.0 (2017/5/25)

See [v1.0.0](https://github.com/SteveDoyle2/pyNastran/releases/tag/v1.0.0) for information regarding enhancements.

### v0.8.0 (2016/8/21)

See [v0.8.0](https://github.com/SteveDoyle2/pyNastran/releases/tag/v0.8.0) for information regarding enhancements.

### v0.7.2 (2015/4/25)

See [v0.7.2](https://github.com/SteveDoyle2/pyNastran/releases) for information regarding enhancements.

### Version 0.6.1 has been released (2013/6)
**Version 0.6** improves BDF reading.  The reader is more robust and also requires proper BDF field formatting (e.g. an integer field can't be a float).  Additionally, cards also have a comment() method.

Marcin Gąsiorek participated in the latest pyNastran under the European Space Agency's (ESA) "Summer of Code In Space" [SOCIS](http://sophia.estec.esa.int/socis2012/?q=node/13) program.  The program provides a stipend to students to work on open-source projects.
He did a great job of simplifying code and creating nicer documentation.
