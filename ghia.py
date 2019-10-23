#!/bin/python
from ghia_cmd import ghia_cmd

if __name__ == "__main__":
    ghia_cmd()
else:
    from ghia_web import create_app