# mne_pipeline_hd
### A [MNE-Python](https://mne.tools/stable/index.html) Pipeline for MEG-Lab Heidelberg
###### inspired by: [Andersen L.M. 2018](https://doi.org/10.3389/fnins.2018.00006)

## Installation
1. Install MNE-python as instructed on the [website](https://www.martinos.org/mne/stable/install_mne_python.html),
I would recommend to install in a separate conda environment with:
`conda env create -n mne_p -f environment.yml`
2. `conda activate mne_p`
3. `pip install --upgrade https://github.com/marsipu/mne_pipeline_hd/zipball/master`

(or do `pip install -e --upgrade https://github.com/marsipu/mne_pipeline_hd/zipball/master`
 when you are in a directory where you want the mne_pipeline_hd-scripts installed)


## Update
Just run `pip install --upgrade https://github.com/marsipu/mne_pipeline_hd/zipball/master` again

## Start
Run `mne_pipeline_hd` in your mne_pipeline-environment (`conda activate mne_p`)

**or**

run \_\_main\_\_.py from the terminal or an IDE like PyCharm, VSCode, Atom, etc.

***When using the pipeline and its functions bear in mind that the pipeline is stil in development 
and the functions are partly still adjusted to my analysis!***

## Bug-Report/Feature-Request
Please report bugs on GitHub as an issue or to me (mne.pipeline@gmail.com) directly.
And if you got ideas on how to improve the pipeline or some feature-requests,
you are welcome to open an issue too or send an e-mail (mne.pipeline@gmail.com)

## Contribute and build your own functions/fix bugs

If you want to help me with the development and/or customize the pipeline to fit your needs, do it like this:

You need a [GitHub-Account](https://github.com/)
and should have [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) installed.

1. Fork this repository on GitHub
2. Move to the folder where you want to clone to
3. Clone **your forked repository** with git from a terminal: `git clone <url you get from the green clone-button from your forked repository on GitHub>`
4. Add upstream to git for updates: `git remote add upstream git://github.com/marsipu/mne_pipeline_hd.git`
5. Create a branch for changes: `git checkout -b <branch-name>`
6. Commit changes: `git commit --all `
7. Push changes to your forked repository on GitHub: `git push`
8. Make "New pull request" from your new feature branch
