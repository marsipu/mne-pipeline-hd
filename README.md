# mne_pipeline_hd
### A [MNE-Python](https://mne.tools/stable/index.html) Pipeline for MEG-Lab Heidelberg
###### based on: [Andersen, L.M., 2018. Group Analysis in MNE-Python of Evoked Responses from a Tactile Stimulation Paradigm: A Pipeline for Reproducibility at Every Step of Processing, Going from Individual Sensor Space Representations to an across-Group Source Space Representation. Front. Neurosci. 12.](https://doi.org/10.3389/fnins.2018.00006)
**Installation**

1. Install MNE-python as instructed on the [website](https://www.martinos.org/mne/stable/install_mne_python.html),
I would recommend to install in a separate conda environment with:
`conda env create -n mne_pipeline -f environment.yml`
2. `conda activate mne_pipeline`
3. `pip install git+https://github.com/marsipu/mne_pipeline_hd.git#egg=mne_pipeline_hd`

**Start**

Start the pipeline in your terminal with `python mne_pipeline_hd`

_or_

Load the Pipeline-folder in an IDE like PyCharm, Spyder, Atom, etc. and run \_\_main\_\_.py

**Contribute and build your own functions/fix bugs**

If you want to customize the pipeline to fit your needs or want to fix bugs, do it like this:
You need a [GitHub-Account](https://github.com/), a working [MNE-Python-Environment](https://www.martinos.org/mne/stable/install_mne_python.html) 
and [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) installed.
You start the pipeline by running \_\_main\_\_.py for example in an IDE.

1. Fork this repository on GitHub
2. Move to the folder where you want to clone to
3. Clone **your forked repository** with git from a terminal: `git clone <url you get from the green clone-button from your forked repository on GitHub>`
4. Add upstream to git for updates: `git remote add upstream git://github.com/marsipu/mne_pipeline_hd.git`
5. Create a branch for changes: `git checkout -b <branch-name>`
6. Commit changes: `git commit --all `
7. Push changes to your forked repository on GitHub: `git push`
8. Make "New pull request" from your new feature branch


Please report bugs on GitHub as an issue or to me directly (mne.pipeline@gmail.com)
