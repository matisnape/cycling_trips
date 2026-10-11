# -*- coding: utf-8 -*-
"""Cienki launcher: python build.py [<slug>] [--watch|--serve]  ->  engine/build.py"""
import os, runpy, sys

ENGINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine", "build.py")
sys.argv[0] = ENGINE
runpy.run_path(ENGINE, run_name="__main__")
