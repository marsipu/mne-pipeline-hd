## Using code from NodeGraphQt
The code for nodes in mne-pipeline-hd is partially copied or heavily inspired by code from
[NodeGraphQt](https://github.com/jchanvfx/NodeGraphQt).
There are various reasons, why this package is not directly used.
Among others this usecase requires some heavy customization and node creation and
implementing new logic seemed to require subclassing a lot of the base objects from NodeGraphQt.
While the original package with its MVC-architecture is very flexible, it is also quite complex.
It supports features, which are not needed here e.g. properties, multiple layouts and widgets.
And last but not least, there is no official support for PySide6/PyQt6 (yet, 2024/04).
NodeGraphQt is licensed under the MIT License.
The license for NodeGraphQt is included [here](./nodegraphqt_license.md).
Thank you to the maintainers of NodeGraphQt especially Johnny Chan for their work.
