# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-

import os


def timestamp(filename: str):
   return os.stat(filename).st_mtime

