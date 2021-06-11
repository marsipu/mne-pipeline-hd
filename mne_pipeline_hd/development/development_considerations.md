#Development Considerations

## Object Consistence
**Controller**, **Main-Window** and **Project** are reinitialized as new objects when changed. 
Thus to maintain the reference to the new objects, in most child-widgets these objects should be accessed from the 
top-level object (e.g. Main-Window, depending on use-case).

## QSettings
On Unix, values stored into QSettings **don't** maintain type and are converted to strings.

## MacOS
- MenuBar
    - at first there was a problem with the native menu-bar on MacOS, which rendered the menu-items unclickable
    - last time checked (2021-06-11) with MacOS 10.14 & 10.16 and PyQt 5.12.9 this issue was gone
- **Modal Dialogs don't have a close-button in the window-top!!!** Thus if no custom modal QDialog is implemented, a "Close"-Button has to be provided for all modal dialogs.
