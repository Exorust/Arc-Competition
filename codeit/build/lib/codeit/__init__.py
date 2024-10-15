# Copyright (c) 2024 Qualcomm Technologies, Inc.
# All Rights Reserved.

import os

location_init_file = os.path.dirname(os.path.realpath(__file__))
print(location_init_file)
PROJECT_FOLDER_PATH = location_init_file.split("codeit")[0]
print(PROJECT_FOLDER_PATH)  