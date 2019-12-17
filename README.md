# mne_pipeline_hd
### A MNE-python Pipeline for MEG-Lab Heidelberg
###### based on: [Andersen, L.M., 2018. Group Analysis in MNE-Python of Evoked Responses from a Tactile Stimulation Paradigm: A Pipeline for Reproducibility at Every Step of Processing, Going from Individual Sensor Space Representations to an across-Group Source Space Representation. Front. Neurosci. 12.](https://doi.org/10.3389/fnins.2018.00006)
**Installation**

1. Install MNE-python as instructed on the [website](https://www.martinos.org/mne/stable/install_mne_python.html),
I would recommend to install in an own conda environment with:
`conda env create -n mne -f environment.yml`
2. `conda actiavte mne`
3. `conda install -c conda-forge pyqt=5.12`
4. Navigate to the folder within the command line where you want the pipeline-script to be installed
5. `pip install -e git+https://github.com/marsipu/mne_pipeline_hd.git#egg=mne_pipeline_hd`
6. Navigate into the first mne_pipeline_hd folder
7. `pip install -r requirements.txt`

**Start**

Start the pipeline from the command line with `python mne_pipeline_hd` (you have to be in ther first "mne_pipeline_hd" directory)

or

Load the Pipeline-folder in an IDE like PyCharm, Spyder, Atom, etc. and run \__main\__.py

**Contribute and build your own functions/fix bugs**

If you want to customize the pipeline to fit your needs or want to fix bugs, do it like this:
You need a [GitHub-Account](https://github.com/), a working [MNE-Python-Environment](https://www.martinos.org/mne/stable/install_mne_python.html) and [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) installed
1. Fork this repository on GitHub
2. Clone **your forked repository** with git from a terminal: `git clone <url you get from the green clone-button from your forked repository on GitHub>`
3. Add upstream to git for updates: `git remote add upstream https://github.com/marsipu/mne_pipeline_hd.git`
4. Create a branch for changes: `git checkout -b <branch-name>`
5. Commit changes: `git commit --all `
6. Push changes to your forked repository on GitHub: `git push`
7. Make "New pull request" from your new feature branch


Please report bugs on GitHub or to me directly (martin.schulz@stud.uni-heidelberg.de)
