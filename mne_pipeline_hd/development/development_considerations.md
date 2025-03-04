#Development Considerations

## Object Consistence

**Controller**, **Main-Window** and **Project** are reinitialized as new
objects when changed.
Thus to maintain the reference to the new objects, in most child-widgets these
objects should be accessed from the
top-level object (e.g. Main-Window, depending on use-case).

## QSettings

On Unix, values stored into QSettings **don't** maintain type and are converted
to strings.

## MacOS

- MenuBar
    - at first there was a problem with the native menu-bar on MacOS, which
      rendered the menu-items unclickable
    - last time checked (2021-06-11) with MacOS 10.14 & 10.16 and PyQt 5.12.9
      this issue was gone
- **Modal Dialogs don't have a close-button in the window-top on MacOS!!!**
  Thus if no custom modal QDialog is implemented, a "Close"-Button should be
  provided for all modal dialogs.

## Multiprocessing

- stdout and stderr are not StdoutStderrStream anymore
- to capture stdout and stderr into the GUI again, there are several
  possibilities with advantages/disadvantages:
    - Pipe: Quick, but stdout and stderr has to be captured by the same
      FileObject to avoid writing on the pipe simultaneously which results in a
      crash (which seems to be the case when an error is raised in the process)
    - Queue: multiprocessing.queue somehow doesn't work when it is passed to
      pool.apply_async-processes. With Manager().queue() this problem is
      solved, but its adds a lot of GUI-blocking time when Manager is first
      initialized.

## Settings vs. QSettings

There are two ways of storing settings and there usecase depends on if the
setting should be device/OS-dependent:

1. A JSON-File, which is stored inside the Home-Path. Settings which should be
   equal for all devices and operating systems should go here (
   e.g. `img_format` or `show_plots`).
2. QSettings(), which is stored by Qt on an OS-depending location and which may
   differ between devices/OS. Settings which dependent on the device/OS should
   go here (e.g. `n_jobs` or `use_cuda`)

## Nodes
Nodes should improve usability and the representation of the pipeline by the following:
- The order of execution is now clearer and renders the function-dependency considerations obsolete.
- The user can now see the input and output of each function.
- Parameters will now go to each function directly, overview only optional
- Using multiple File-Lists or Projets side-by-side will be more easy to handle.
-

## Custom Functions Overhaul
- Instead of using meeg/fsmri in functions the data-type (which then should be reserved namespaces like "raw" or "epochs") can be used. Maybe that makes meeg/fsmri obsolete in the end but for group analysis group is still handy.
- data-types need to be declared and visible somewhere
