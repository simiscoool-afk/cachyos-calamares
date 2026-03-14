#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2016 Artoo <artoo@manjaro.org>
#   SPDX-FileCopyrightText: 2017 Alf Gaida <agaida@siduction.org>
#   SPDX-FileCopyrightText: 2018 Gabriel Craciunescu <crazy@frugalware.org>
#   SPDX-FileCopyrightText: 2019 Adriaan de Groot <groot@kde.org>
#   SPDX-License-Identifier: GPL-3.0-or-later
#
#   Calamares is Free Software: see the License-Identifier above.
#

import os

import libcalamares

from libcalamares.utils import debug, target_env_call

import gettext
_ = gettext.translation("calamares-python",
                        localedir=libcalamares.utils.gettext_path(),
                        languages=libcalamares.utils.gettext_languages(),
                        fallback=True).gettext

# AMD PCI vendor ID
AMD_VENDOR_ID = "0x1002"
# PCI display device classes (VGA controller and 3D controller)
DISPLAY_CLASSES = ("0x030000", "0x030200", "0x038000")


def pretty_name():
    return _("Configure Plymouth theme")


def detect_plymouth():
    """
    Checks existence (runnability) of plymouth in the target system.

    @return True if plymouth exists in the target, False otherwise
    """
    # Used to only check existence of path /usr/bin/plymouth in target
    return target_env_call(["sh", "-c", "which plymouth"]) == 0


def detect_amdgpu():
    """
    Checks if an AMD GPU is present by reading PCI device info from sysfs.

    @return True if an AMD GPU is detected, False otherwise
    """
    pci_devices = "/sys/bus/pci/devices"
    try:
        for device in os.listdir(pci_devices):
            device_path = os.path.join(pci_devices, device)
            vendor_path = os.path.join(device_path, "vendor")
            class_path = os.path.join(device_path, "class")
            try:
                with open(vendor_path, "r") as f:
                    vendor = f.read().strip()
                with open(class_path, "r") as f:
                    dev_class = f.read().strip()
            except OSError:
                continue
            if vendor == AMD_VENDOR_ID and dev_class in DISPLAY_CLASSES:
                debug("Detected AMD GPU: {}".format(device))
                return True
    except OSError:
        debug("Could not read PCI devices from sysfs")
    return False


class PlymouthController:

    def __init__(self):
        self.__root = libcalamares.globalstorage.value('rootMountPoint')

    @property
    def root(self):
        return self.__root

    def setTheme(self):
        config = libcalamares.job.configuration
        plymouth_theme = config["plymouth_theme"]

        if config.get("plymouth_theme_amdgpu") and detect_amdgpu():
            plymouth_theme = config["plymouth_theme_amdgpu"]
            debug("Using AMD GPU plymouth theme: {}".format(plymouth_theme))

        target_env_call(["plymouth-set-default-theme", plymouth_theme])

    def run(self):
        if detect_plymouth():
            if (("plymouth_theme" in libcalamares.job.configuration) and
               (libcalamares.job.configuration["plymouth_theme"] is not None)):
                self.setTheme()
        return None


def run():
    pc = PlymouthController()
    return pc.run()
