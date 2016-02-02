RnsUtils
========

RnsUtils is Renoise related library and companion utility.
It is meant for developers aiming to use generate renoise file or renoise users wanting to convert SoundFont 2 or SFZ to renoise instruments,
reencode instruments to .flac or .ogg, manipulate tags and comments in instruments or organise a xrni library based on those tags.

Installation
------------

RnsUtils is installable from PyPI with a single pip command::

    pip install rnsutils

Alternatively, RnsUtils can be run directly from sources after a git pull::

    git clone https://gitlab.com/zeograd/rnsutils.git
    cd rnsutils && python setup.py install


sf2toxrni
---------

**sf2toxrni** is a command line utility which convert SoundFont 2 instruments into renoise instruments (.xrni).
It parses a SoundFont 2 file instrument list and generate one .xnri file for each instrument using as much information
from the SoundFont 2 instrument properties (generators) as possible. All read properties will be injected in a template
renoise instrument.

::
    usage: sf2toxrni [-h] [-d] [-e {none,flac,ogg}] [-f] [-q] [-u] [--no-unused]
                     [-o OUTPUT_DIR] [-t TEMPLATE]
                     sf2_filename [sf2_filename ...]

    GPL v3+ 2016 Olivier Jolly

    positional arguments:
      sf2_filename          input file in SoundFont2 format

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug parsing [default: False]
      -e {none,flac,ogg}, --encode {none,flac,ogg}
                            encode samples into given format [default: flac]
      -f, --force           force overwriting existing files [default: False]
      -q, --quiet           quiet operation [default: False]
      -u, --unused          show unused generators [default: True]
      --no-unused
      -o OUTPUT_DIR, --ouput-dir OUTPUT_DIR
                            output directory [default: current directory]
      -t TEMPLATE           template filename [default: empty-31.xrni]

    Convert sf2 file into renoise instrument


Use the *-o* option to specify a destination directory and *--no-unused* if you don't want to see the list of generators
which are present in the SoundFont 2 file but were not used in generating the .xnri.

*-t* allows to change the template .xnri, one is provided by default and works with renoise 3.1 at least. If you want
different default settings or generate instruments for a different version, you can provide a template of your own
and specify its filename. If the filename is not found on the filesystem, it will be looked up in the default
data patch for the python package.
If you want to provide your own template, it must follow the recommendations of the following section.

template
........

A template .xnri file will be used to have Soundfont 2 properties injected to produce a final, customized .xnri file.
It must contains at least one sample. The first sample will be used as template for all samples, others will be discarded.
The first sample must have an ADHSR modulation on volume and the filter set to a Low pass filter.
SoundFont 2 reverb and chorus effects will be mapped respectively on macro 1 and macro 2, so you may want to map those macros
on input of DSP chains to control the dry/wet amount of those effects.
You may use macro 3 and up to your liking.

compliance and limitations
..........................

The set of features found in a SoundFont 2 and .xnri doesn't fully overlap, hence this converter won't produce
a bit wise exact instrument.
First, SoundFont 2 files contains presets, which are mapped to one or more instruments. Those presets might alter how
the instruments sound, but it's a bad practice and usually only map keys range to instruments. This converter works
from SoundFont 2 instruments only.

**sf2toxrni** supports :
    * envelope volume release
    * sample panning
    * sample looping
    * sample tuning (base note, fine and coarse tuning)
    * key mapping
    * velocity mapping
    * low pass filter cutoff
    * chorus amount
    * reverb amount

**sf2toxrni** does not support :
    * vibrato
    * initial volume attenuation (always minus infinite in result, it seems like it'd be a pita to support otherwise)

sfztoxrni
---------

Similarly to the **sf2toxrni** converter, **sfztoxrni** convert SFZ files into renoise instruments (.xrni).
Renoise supporting now natively SFZ files, this converter is only useful on SFZ instruments needing
more than one modulation set (different ADHSR settings depending on the velocity/key mapping) or
a more aggressive sample filename search (like for SFZ built under case insensitive filesystem and read in
case sensitive filesystem). As SFZ support in Renoise will progress, this converter will be deprecated.

::
    usage: sfztoxrni [-h] [-d] [-e {none,flac,ogg}] [-f] [-q] [-o OUTPUT_DIR]
                     [-t TEMPLATE] [-u] [--no-unused]
                     sfz_filename [sfz_filename ...]

    GPL v3+ 2016 Olivier Jolly

    positional arguments:
      sfz_filename          input file in SFZ format

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug parsing [default: False]
      -e {none,flac,ogg}, --encode {none,flac,ogg}
                            encode samples into given format [default: flac]
      -f, --force           force overwriting existing files [default: False]
      -q, --quiet           quiet operation [default: False]
      -o OUTPUT_DIR, --ouput-dir OUTPUT_DIR
                            output directory [default: current directory]
      -t TEMPLATE           template filename [default: empty-31.xrni]
      -u, --unused          show unused generators [default: True]
      --no-unused

    Convert SFZ file into renoise instrument


xrnireencode
------------

**Xrnireencode** is a command line utility to reencode samples in renoise instrument (.xrni).
It can convert to **flac** or **ogg** one or more instruments given on command line.

::

    usage: xrnireencode [-h] [-d] [-e {flac,ogg}] [-q] [-o OUTPUT_DIR]
                        xrni_filename [xrni_filename ...]

    GPL v3+ 2016 Olivier Jolly

    positional arguments:
      xrni_filename         input file in XRNI format

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug parsing [default: False]
      -e {flac,ogg}, --encode {flac,ogg}
                            encode samples into given format [default: flac]
      -q, --quiet           quiet operation [default: False]
      -o OUTPUT_DIR, --ouput-dir OUTPUT_DIR
                            output directory [default: current directory]

    Reencode samples in renoise instrument

xrnicomment
-----------

**xrnicomment** is a command line utility to manipulate comments in renoise instruments (.xrni).
It can read, clear, replace and append content to the comment in one or more xrni files.
It is compatible with renoise 3.0+ instruments and intercompatible with "instrument info" tool
( http://forum.renoise.com/index.php/topic/43434-new-tool-30-instrument-info/ ).

::

    usage: xrnicomment [-h] [-d] [-a] [-e] [-m MESSAGE] [-r] [-v]
                       xrni_filename [xrni_filename ...]

    GPL v3+ 2016 Olivier Jolly

    positional arguments:
      xrni_filename         input file in XRNI format

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug parsing [default: False]
      -a, --append          append to comment
      -e, --edit            edit comment
      -m MESSAGE, --message MESSAGE
                            edit message content [default reads from standard
                            input]
      -r, --remove          remove comment
      -v, --view            view comment [default action]

    Display or change XRNI comments

xrnitag
-------

**xrnitag** is a command line utility to manipulate tags in renoise instruments (.xrni).
It can read, clear, remove or add tag to the tag list in one or more xrni files.
If you want to edit a tag, you can remove it and then add the new one.
**xrnitag** is compatible with renoise 3.0+ instruments and intercompatible with "instrument info" tool
( http://forum.renoise.com/index.php/topic/43434-new-tool-30-instrument-info/ ).

::

    usage: xrnitag [-h] [-d] [-a TAGS_TO_ADD] [-c] [-r TAGS_TO_REMOVE] [-v]
                   xrni_filename [xrni_filename ...]

    GPL v3+ 2016 Olivier Jolly

    positional arguments:
      xrni_filename         input file in XRNI format

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug parsing [default: False]
      -a TAGS_TO_ADD, --add TAGS_TO_ADD
                            add a tag
      -c, --clear           clear all tags
      -r TAGS_TO_REMOVE, --remove TAGS_TO_REMOVE
                            remove a tag
      -v, --view            view all tags [default action]

    Display or change XRNI tags

xrniorganise
------------

**xrniorganise** is a command line utility to organise your renoise instruments (.xrni) by tags.
It creates a view of your instrument library using instrument tags, until renoise features a native tag
powered instrument library search.
Using symbolic links to create instruments views, it is only compatible with unix OSes (patches for
supporting other OSes are welcome).

Instruments which aren't tagged at all will be linked into the "untagged" directory.

Note that you can incrementally populate your library view, as **xrniorganise** will not remove existing
instruments. It also means that if you switch a tag from *old* to *new* and run **xrniorganise** again,
your instrument(s) will be linked both in the *old* and *new* directories. When you rename or remove tags,
you can use the *-c* command line argument which makes so that your destination directory is cleaned before
having any link created.

Directory cleaning attempts to be as conservative as possible (it's a recursive removal after all, it could
damage stuff if broken) by only removing symbolic links and empty directories. It implies that any regular file
you'll place inside the destination directory will abort cleaning.

Here is an example session:

.. code:: shell

    # initially, we have some untagged, unsorted xrni files

    $ find unsorted_xrni/ sorted_xrni/

    unsorted_xrni/
    unsorted_xrni/0_Arco Strings.xrni
    unsorted_xrni/6_Zip.xrni
    unsorted_xrni/0_Flute.xrni
    unsorted_xrni/8_Oboe.xrni

    sorted_xrni/

    # we tag them with xrnitag CLI (or "instrument info" tool)

    $ xrnitag -a orchestral unsorted_xrni/0_Arco\ Strings.xrni unsorted_xrni/0_Flute.xrni unsorted_xrni/8_Oboe.xrni
    $ xrnitag -a sfx unsorted_xrni/6_Zip.xrni
    $ xrnitag -a woodwind unsorted_xrni/0_Flute.xrni unsorted_xrni/8_Oboe.xrni
    $ xrnitag -a loop unsorted_xrni/6_Zip.xrni unsorted_xrni/8_Oboe.xrni unsorted_xrni/0_Arco\ Strings.xrni

    # them, we create a library view based on those tags

    $ xrniorganise -o sorted_xrni/ unsorted_xrni/*

    # now, you can see links to actual instruments based on their tags

    $ find unsorted_xrni/ sorted_xrni/

    unsorted_xrni/
    unsorted_xrni/0_Arco Strings.xrni
    unsorted_xrni/6_Zip.xrni
    unsorted_xrni/0_Flute.xrni
    unsorted_xrni/8_Oboe.xrni

    sorted_xrni/
    sorted_xrni/woodwind
    sorted_xrni/woodwind/0_Flute.xrni
    sorted_xrni/woodwind/8_Oboe.xrni
    sorted_xrni/loop
    sorted_xrni/loop/0_Arco Strings.xrni
    sorted_xrni/loop/6_Zip.xrni
    sorted_xrni/loop/8_Oboe.xrni
    sorted_xrni/sfx
    sorted_xrni/sfx/6_Zip.xrni
    sorted_xrni/orchestral
    sorted_xrni/orchestral/0_Arco Strings.xrni
    sorted_xrni/orchestral/0_Flute.xrni
    sorted_xrni/orchestral/8_Oboe.xrni

Here is the summary of all options::

    usage: xrniorganise [-h] [-d] [-c] [-n] [-r] -o OUTPUT_DIR
                        xrni_filename [xrni_filename ...]

    GPL v3+ 2016 Olivier Jolly

    positional arguments:
      xrni_filename         input file in XRNI format

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug parsing [default: False]
      -c, --clean           clean destination directory before operations
      -n, --dry-run         don't actually perform filesystem operations [default:
                            False]
      -r, --recursive       recursively parse directories [default: False]
      -o OUTPUT_DIR, --ouput-dir OUTPUT_DIR
                            output directory

    Organise XRNI according to their tags




Library use
-----------

Current, only renoise instrument API is available.
A renoise instrument is represented by the **RenoiseInstrument** class and can be loaded that way::

    from rnsutils.instrument import RenoiseInstrument
    # load an instrument from an existing xnri
    inst = RenoiseInstrument('existing.xrni')
    # now, inst.root is an objectified xml tree you can access and alter
    # inst.sample_data is a mutable list of audio files content
    inst.save('new.xrni')
