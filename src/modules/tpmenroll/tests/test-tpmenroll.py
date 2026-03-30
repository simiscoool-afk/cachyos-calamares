# SPDX-FileCopyrightText: no
# SPDX-License-Identifier: CC0-1.0
#
import os
import tempfile
import types

import libcalamares

libcalamares.globalstorage = libcalamares.GlobalStorage(None)


class Job(object):
    def __init__(self):
        self.configuration = {
            "defaultPcrs": "11",
            "supportedPcrs": ["11", "4"],
            "tpm2Device": "auto",
        }


libcalamares.job = Job()

from src.modules.tpmenroll import main


assert main.should_auto_enroll("grub", None) is False
assert main.should_auto_enroll("systemd-boot-uki", None) is True
assert main.should_auto_enroll("systemd-boot-uki", False) is False

root_partition = main.find_encrypted_root_partition(
    [
        {"mountPoint": "/boot", "device": "/dev/vda1"},
        {
            "mountPoint": "/",
            "device": "/dev/vda2",
            "luksMapperName": "cryptroot",
            "luksPassphrase": "secret",
        },
    ]
)
assert root_partition["device"] == "/dev/vda2"
assert main.find_encrypted_root_partition([{"mountPoint": "/", "device": "/dev/vda2"}]) is None

assert main.resolve_pcrs(libcalamares.job.configuration, "") == "11"
assert main.resolve_pcrs(libcalamares.job.configuration, "4") == "4"
assert main.resolve_pcrs({"defaultPcrs": 11, "supportedPcrs": [11, 4]}, "") == "11"
assert main.resolve_pcrs({"defaultPcrs": 11, "supportedPcrs": [11, 4]}, 4) == "4"
try:
    main.resolve_pcrs(libcalamares.job.configuration, "7")
    raise AssertionError("Unsupported PCRs should fail")
except ValueError:
    pass

assert main.build_enroll_command("/dev/vda2", "11", "auto") == [
    "systemd-cryptenroll",
    "--tpm2-device=auto",
    "--tpm2-pcrs=11",
    "/dev/vda2",
]


def reset_global_storage():
    libcalamares.globalstorage = libcalamares.GlobalStorage(None)
    return libcalamares.globalstorage


gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "grub")
assert main.run() is None

gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("tpmAutoEnroll", False)
assert main.run() is None

gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("tpmAutoEnroll", True)
assert main.run() is None

gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("partitions", [{"mountPoint": "/", "device": "/dev/vda2", "luksMapperName": "cryptroot", "luksPassphrase": "secret"}])
old_host_has_tpm = main.host_has_tpm
try:
    main.host_has_tpm = lambda: False
    error = main.run()
    assert error[0] == "TPM Configuration Error"
finally:
    main.host_has_tpm = old_host_has_tpm

gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("partitions", [{"mountPoint": "/", "device": "/dev/vda2", "luksMapperName": "cryptroot", "luksPassphrase": "secret"}])

with tempfile.TemporaryDirectory() as tmpdir:
    os.makedirs(os.path.join(tmpdir, "etc"))
    crypttab_path = os.path.join(tmpdir, "etc", "crypttab")
    with open(crypttab_path, "w") as f:
        f.write("# /etc/crypttab\n")
        f.write("cryptroot             UUID=abcd-1234                         none luks\n")
    gs.insert("rootMountPoint", tmpdir)

    old_host_has_tpm = main.host_has_tpm
    old_enroll_tpm2 = main.enroll_tpm2
    try:
        main.host_has_tpm = lambda: True
        main.enroll_tpm2 = lambda device, passphrase, pcrs, tpm2_device: (
            main.build_enroll_command(device, pcrs, tpm2_device),
            types.SimpleNamespace(returncode=0, stdout="", stderr=""),
        )
        assert main.run() is None
        assert libcalamares.globalstorage.value("tpmAutoEnroll") == True
        assert libcalamares.globalstorage.value("tpmAutoEnrollPcrs") == "11"

        with open(crypttab_path, "r") as f:
            content = f.read()
        assert "tpm2-device=auto" in content
        assert "luks,tpm2-device=auto" in content
    finally:
        main.host_has_tpm = old_host_has_tpm
        main.enroll_tpm2 = old_enroll_tpm2

# Test update_crypttab standalone
with tempfile.TemporaryDirectory() as tmpdir:
    os.makedirs(os.path.join(tmpdir, "etc"))
    crypttab_path = os.path.join(tmpdir, "etc", "crypttab")

    # Test: appends tpm2-device to existing options
    with open(crypttab_path, "w") as f:
        f.write("cryptroot UUID=abcd-1234 none luks\n")
    assert main.update_crypttab(tmpdir, "cryptroot", "auto") is True
    with open(crypttab_path, "r") as f:
        assert "luks,tpm2-device=auto" in f.read()

    # Test: idempotent — does not duplicate if already present
    assert main.update_crypttab(tmpdir, "cryptroot", "auto") is True
    with open(crypttab_path, "r") as f:
        content = f.read()
    assert content.count("tpm2-device=") == 1

    # Test: returns False for unknown mapper
    assert main.update_crypttab(tmpdir, "nonexistent", "auto") is False

# Test: GS not written when enrollment is skipped (no encrypted root)
gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("tpmAutoEnroll", True)
assert main.run() is None
assert not gs.contains("tpmAutoEnrollPcrs") or gs.value("tpmAutoEnrollPcrs") != "11"
