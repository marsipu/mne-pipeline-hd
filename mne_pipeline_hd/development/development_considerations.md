#Development Considerations

## Object Consistence
**Controller**, **Main-Window** and **Project** are reinitialized as new objects when changed. 
Thus to maintain the reference to the new objects, in most child-widgets these objects should be accessed from the 
top-level object (e.g. Main-Window, depending on use-case).

## QSettings
On Unix, values stored into QSettings **don't** maintain type and are converted to strings.
