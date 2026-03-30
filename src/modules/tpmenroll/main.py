#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2026 CachyOS contributors
#   SPDX-License-Identifier: GPL-3.0-or-later
#

import os
import subprocess

import libcalamares

import gettext

_ = gettext.translation(
    "calamares-python",
    localedir=libcalamares.utils.gettext_path(),
    languages=libcalamares.utils.gettext_languages(),
    fallback=True,
).gettext

SYSTEMD_BOOT_UKI = "systemd-boot-uki"
DEFAULT_PCRS = "11"
DEFAULT_SUPPORTED_PCRS = ["11", "4"]
DEFAULT_TPM2_DEVICE = "auto"
TPM_AUTO_ENROLL_KEY = "tpmAutoEnroll"
TPM_AUTO_ENROLL_PCRS_KEY = "tpmAutoEnrollPcrs"


def pretty_name():
    return _("Enrolling TPM2 unlock.")


def host_has_tpm():
    return any(
        os.path.exists(path)
        for path in ("/sys/class/tpm/tpm0", "/dev/tpmrm0", "/dev/tpm0")
    )


def find_encrypted_root_partition(partitions):
    for partition in partitions or []:
        if (
            partition.get("mountPoint") == "/"
            and partition.get("luksMapperName")
            and partition.get("device")
        ):
            return partition
    return None


def should_auto_enroll(bootloader, auto_enroll):
    if bootloader != SYSTEMD_BOOT_UKI:
        return False

    if auto_enroll is None:
        return True

    return bool(auto_enroll)


def normalize_pcr_value(value, default=""):
    if value is None:
        return default

    normalized = str(value).strip()
    return normalized if normalized else default


def normalize_supported_pcrs(values):
    if values is None:
        values = DEFAULT_SUPPORTED_PCRS

    if isinstance(values, (str, int)):
        values = [values]

    normalized = [normalize_pcr_value(value) for value in values]
    normalized = [value for value in normalized if value]

    return normalized or list(DEFAULT_SUPPORTED_PCRS)


def resolve_pcrs(configuration, global_storage_pcrs):
    pcrs = normalize_pcr_value(global_storage_pcrs) or normalize_pcr_value(
        configuration.get("defaultPcrs", DEFAULT_PCRS),
        DEFAULT_PCRS,
    )
    supported_pcrs = normalize_supported_pcrs(configuration.get("supportedPcrs", DEFAULT_SUPPORTED_PCRS))

    if pcrs not in supported_pcrs:
        raise ValueError(
            f"Unsupported TPM PCR policy '{pcrs}'. Allowed values: {', '.join(supported_pcrs)}."
        )

    return pcrs


def build_enroll_command(device, pcrs, tpm2_device):
    return [
        "systemd-cryptenroll",
        f"--tpm2-device={tpm2_device}",
        f"--tpm2-pcrs={pcrs}",
        device,
    ]


def enroll_tpm2(device, passphrase, pcrs, tpm2_device):
    command = build_enroll_command(device, pcrs, tpm2_device)
    result = subprocess.run(
        command,
        input=passphrase + "\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return command, result


def run():
    global_storage = libcalamares.globalstorage
    bootloader = global_storage.value("packagechooser_bootloader")
    auto_enroll = global_storage.value(TPM_AUTO_ENROLL_KEY) if global_storage.contains(TPM_AUTO_ENROLL_KEY) else None

    if not should_auto_enroll(bootloader, auto_enroll):
        libcalamares.utils.debug("Skipping TPM enrollment for non-UKI bootloader selection.")
        return None

    try:
        pcrs = resolve_pcrs(
            libcalamares.job.configuration,
            global_storage.value(TPM_AUTO_ENROLL_PCRS_KEY) if global_storage.contains(TPM_AUTO_ENROLL_PCRS_KEY) else "",
        )
    except ValueError as error:
        return (_("Configuration Error"), str(error))

    global_storage.insert(TPM_AUTO_ENROLL_KEY, True)
    global_storage.insert(TPM_AUTO_ENROLL_PCRS_KEY, pcrs)

    root_partition = find_encrypted_root_partition(global_storage.value("partitions"))
    if not root_partition:
        libcalamares.utils.debug("Skipping TPM enrollment because there is no encrypted root partition.")
        return None

    if not host_has_tpm():
        return (
            _("TPM Configuration Error"),
            _("TPM auto-enrollment was requested for <pre>systemd-boot-uki</pre>, but no TPM device is available."),
        )

    passphrase = root_partition.get("luksPassphrase", "")
    if not passphrase:
        return (
            _("TPM Configuration Error"),
            _("The encrypted root partition is missing a usable LUKS passphrase for TPM enrollment."),
        )

    device = root_partition["device"]
    tpm2_device = libcalamares.job.configuration.get("tpm2Device", DEFAULT_TPM2_DEVICE)
    libcalamares.utils.debug(f"Enrolling TPM2 unlock for {device} with PCR policy {pcrs}.")

    try:
        command, result = enroll_tpm2(device, passphrase, pcrs, tpm2_device)
    except subprocess.TimeoutExpired:
        return (
            _("TPM Enrollment Error"),
            _("Timed out while enrolling TPM unlock for the encrypted root partition."),
        )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        libcalamares.utils.warning(
            f"TPM enrollment command failed for {device}: {stderr or stdout or 'unknown error'}"
        )
        return (
            _("TPM Enrollment Error"),
            _("Failed to enroll TPM unlock for the encrypted root partition with <pre>{}</pre>.").format(
                " ".join(command)
            ),
        )

    return None
