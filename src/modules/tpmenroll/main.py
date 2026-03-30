#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2026 CachyOS contributors
#   SPDX-License-Identifier: GPL-3.0-or-later
#

import os
import re
import subprocess

import libcalamares

from libcalamares.utils import check_target_env_call

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

REENROLL_SCRIPT_PATH = "/usr/local/bin/cachyos-tpm-reenroll"
REENROLL_SERVICE_NAME = "cachyos-tpm-reenroll.service"


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
    supported_pcrs = normalize_supported_pcrs(
        configuration.get("supportedPcrs", DEFAULT_SUPPORTED_PCRS)
    )
    if pcrs not in supported_pcrs:
        raise ValueError(
            f"Unsupported TPM PCR policy '{pcrs}'. "
            f"Allowed values: {', '.join(supported_pcrs)}."
        )
    return pcrs


def write_text_file(path, content, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    if mode is not None:
        os.chmod(path, mode)


def build_enroll_command(device, tpm2_device):
    """Build initial enrollment command with no PCR binding."""
    return [
        "systemd-cryptenroll",
        f"--tpm2-device={tpm2_device}",
        "--tpm2-pcrs=",
        device,
    ]


def enroll_tpm2(device, passphrase, tpm2_device):
    """Enroll TPM2 with no PCR binding (for install-time use)."""
    command = build_enroll_command(device, tpm2_device)
    result = subprocess.run(
        command,
        input=passphrase + "\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return command, result


def update_crypttab(root_mount_point, mapper_name, tpm2_device):
    """Add tpm2-device= to the crypttab entry for the given mapper name."""
    crypttab_path = os.path.join(root_mount_point, "etc", "crypttab")
    if not os.path.isfile(crypttab_path):
        libcalamares.utils.warning(
            f"Cannot update crypttab: {crypttab_path} does not exist."
        )
        return False

    with open(crypttab_path, "r") as f:
        lines = f.readlines()

    tpm2_option = f"tpm2-device={tpm2_device}"
    updated = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) >= 1 and fields[0] == mapper_name:
            if "tpm2-device=" in stripped:
                updated = True
                break
            if len(fields) >= 4:
                lines[i] = re.sub(
                    r"(\S+\s+\S+\s+\S+\s+)(.*)",
                    rf"\1\2,{tpm2_option}",
                    line.rstrip(),
                ) + "\n"
            else:
                lines[i] = line.rstrip() + f" {tpm2_option}\n"
            updated = True
            break

    if not updated:
        libcalamares.utils.warning(
            f"Could not find crypttab entry for mapper '{mapper_name}'."
        )
        return False

    with open(crypttab_path, "w") as f:
        f.writelines(lines)

    libcalamares.utils.debug(
        f"Updated crypttab: added {tpm2_option} to entry '{mapper_name}'."
    )
    return True


def get_stable_device_path(partition):
    """Return a stable device path using LUKS UUID, falling back to raw device."""
    luks_uuid = partition.get("luksUuid", "")
    if luks_uuid:
        return f"/dev/disk/by-uuid/{luks_uuid}"
    return partition["device"]


def reenroll_script(device, pcrs, tpm2_device):
    return f"""#!/usr/bin/env bash
set -eu

# Re-enroll TPM2 with proper PCR policy binding.
# The initial enrollment (during installation) sealed the key without PCR
# binding so that first boot could auto-unlock.  This script replaces that
# with a PCR-bound policy now that the installed system has booted and the
# PCR state reflects the actual boot chain.

TAG="cachyos-tpm-reenroll"

logger -t "$TAG" "Re-enrolling TPM2 with PCR policy {pcrs} for {device}..."

if systemd-cryptenroll \\
    --wipe-slot=tpm2 \\
    "--tpm2-device={tpm2_device}" \\
    "--tpm2-pcrs={pcrs}" \\
    "--unlock-tpm2-device={tpm2_device}" \\
    "{device}"; then
    logger -t "$TAG" "TPM2 re-enrollment succeeded."
    rm -f "$0"
else
    logger -t "$TAG" -p err "TPM2 re-enrollment failed (exit $?). Will retry on next boot."
    exit 1
fi
"""


def reenroll_service():
    return f"""[Unit]
Description=Re-enroll TPM2 with PCR policy after first boot
ConditionPathExists={REENROLL_SCRIPT_PATH}
After=cryptsetup.target local-fs.target

[Service]
Type=oneshot
ExecStart={REENROLL_SCRIPT_PATH}

[Install]
WantedBy=multi-user.target
"""


def install_reenroll_service(root_mount_point, device, pcrs, tpm2_device):
    write_text_file(
        root_mount_point + REENROLL_SCRIPT_PATH,
        reenroll_script(device, pcrs, tpm2_device),
        0o755,
    )
    write_text_file(
        os.path.join(
            root_mount_point, "etc", "systemd", "system", REENROLL_SERVICE_NAME
        ),
        reenroll_service(),
    )
    check_target_env_call(["systemctl", "enable", REENROLL_SERVICE_NAME])


def run():
    global_storage = libcalamares.globalstorage
    bootloader = global_storage.value("packagechooser_bootloader")
    auto_enroll = (
        global_storage.value(TPM_AUTO_ENROLL_KEY)
        if global_storage.contains(TPM_AUTO_ENROLL_KEY)
        else None
    )

    if not should_auto_enroll(bootloader, auto_enroll):
        libcalamares.utils.debug(
            "Skipping TPM enrollment for non-UKI bootloader selection."
        )
        return None

    try:
        pcrs = resolve_pcrs(
            libcalamares.job.configuration,
            global_storage.value(TPM_AUTO_ENROLL_PCRS_KEY)
            if global_storage.contains(TPM_AUTO_ENROLL_PCRS_KEY)
            else "",
        )
    except ValueError as error:
        return (_("Configuration Error"), str(error))

    root_partition = find_encrypted_root_partition(
        global_storage.value("partitions")
    )
    if not root_partition:
        libcalamares.utils.debug(
            "Skipping TPM enrollment because there is no encrypted root partition."
        )
        return None

    if not host_has_tpm():
        return (
            _("TPM Configuration Error"),
            _(
                "TPM auto-enrollment was requested for "
                "<pre>systemd-boot-uki</pre>, but no TPM device is available."
            ),
        )

    passphrase = root_partition.get("luksPassphrase", "")
    if not passphrase:
        return (
            _("TPM Configuration Error"),
            _(
                "The encrypted root partition is missing a usable LUKS "
                "passphrase for TPM enrollment."
            ),
        )

    device = root_partition["device"]
    tpm2_device = libcalamares.job.configuration.get(
        "tpm2Device", DEFAULT_TPM2_DEVICE
    )
    root_mount_point = global_storage.value("rootMountPoint")
    mapper_name = root_partition.get("luksMapperName", "")

    libcalamares.utils.debug(
        f"Enrolling TPM2 (no PCR binding) for {device}; "
        f"first-boot service will re-enroll with PCR policy {pcrs}."
    )

    # Phase 1: Enroll with no PCR binding so first boot auto-unlocks.
    # During installation the PCR state reflects the live ISO, not the
    # installed system, so binding to PCRs now would cause unlock failure.
    try:
        command, result = enroll_tpm2(device, passphrase, tpm2_device)
    except subprocess.TimeoutExpired:
        return (
            _("TPM Enrollment Error"),
            _(
                "Timed out while enrolling TPM unlock for the encrypted "
                "root partition."
            ),
        )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        libcalamares.utils.warning(
            f"TPM enrollment command failed for {device}: "
            f"{stderr or stdout or 'unknown error'}"
        )
        return (
            _("TPM Enrollment Error"),
            _(
                "Failed to enroll TPM unlock for the encrypted root "
                "partition with <pre>{}</pre>."
            ).format(" ".join(command)),
        )

    global_storage.insert(TPM_AUTO_ENROLL_KEY, True)
    global_storage.insert(TPM_AUTO_ENROLL_PCRS_KEY, pcrs)

    # Update crypttab so systemd tries TPM2 unlock on boot
    if root_mount_point and mapper_name:
        update_crypttab(root_mount_point, mapper_name, tpm2_device)

    # Phase 2: Install first-boot service that re-enrolls with proper PCR
    # binding using --unlock-tpm2-device to authenticate via the existing
    # (unbound) TPM2 token, then replaces it with a PCR-bound one.
    if root_mount_point:
        stable_device = get_stable_device_path(root_partition)
        install_reenroll_service(
            root_mount_point, stable_device, pcrs, tpm2_device
        )

    return None
