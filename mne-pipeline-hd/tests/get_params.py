import os


def get_parameters():
    with open(os.getcwd() + 'resources/parameters_template.py', 'r') as p:
        for line in p:
            pass


if __name__ == __main__:
    get_parameters()
