# SPDX-FileCopyrightText: no
# SPDX-License-Identifier: CC0-1.0
#
import os
import stat
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


# --- should_auto_enroll ---

assert main.should_auto_enroll("grub", None) is False
assert main.should_auto_enroll("systemd-boot-uki", None) is True
assert main.should_auto_enroll("systemd-boot-uki", False) is False
assert main.should_auto_enroll("systemd-boot-uki", True) is True

# --- find_encrypted_root_partition ---

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
assert main.find_encrypted_root_partition(
    [{"mountPoint": "/", "device": "/dev/vda2"}]
) is None

# --- resolve_pcrs ---

assert main.resolve_pcrs(libcalamares.job.configuration, "") == "11"
assert main.resolve_pcrs(libcalamares.job.configuration, "4") == "4"
assert main.resolve_pcrs({"defaultPcrs": 11, "supportedPcrs": [11, 4]}, "") == "11"
assert main.resolve_pcrs({"defaultPcrs": 11, "supportedPcrs": [11, 4]}, 4) == "4"
try:
    main.resolve_pcrs(libcalamares.job.configuration, "7")
    raise AssertionError("Unsupported PCRs should fail")
except ValueError:
    pass

# --- build_enroll_command (no PCR binding) ---

assert main.build_enroll_command("/dev/vda2", "auto") == [
    "systemd-cryptenroll",
    "--tpm2-device=auto",
    "--tpm2-pcrs=",
    "/dev/vda2",
]

# --- get_stable_device_path ---

assert (
    main.get_stable_device_path({"device": "/dev/vda2", "luksUuid": "abcd-1234"})
    == "/dev/disk/by-uuid/abcd-1234"
)
assert main.get_stable_device_path({"device": "/dev/vda2"}) == "/dev/vda2"

# --- reenroll_script ---

script = main.reenroll_script("/dev/disk/by-uuid/abcd-1234", "11", "auto")
assert "systemd-cryptenroll" in script
assert "--wipe-slot=tpm2" in script
assert "--tpm2-pcrs=11" in script
assert "--unlock-tpm2-device=auto" in script
assert "/dev/disk/by-uuid/abcd-1234" in script
assert "logger" in script

# --- reenroll_service ---

service = main.reenroll_service()
assert main.REENROLL_SCRIPT_PATH in service
assert "oneshot" in service
assert "multi-user.target" in service
assert "ConditionPathExists" in service
assert "cryptsetup.target" in service

# --- update_crypttab ---

with tempfile.TemporaryDirectory() as tmpdir:
    os.makedirs(os.path.join(tmpdir, "etc"))
    crypttab_path = os.path.join(tmpdir, "etc", "crypttab")

    # Appends tpm2-device to existing options
    with open(crypttab_path, "w") as f:
        f.write("cryptroot UUID=abcd-1234 none luks\n")
    assert main.update_crypttab(tmpdir, "cryptroot", "auto") is True
    with open(crypttab_path, "r") as f:
        assert "luks,tpm2-device=auto" in f.read()

    # Idempotent — does not duplicate
    assert main.update_crypttab(tmpdir, "cryptroot", "auto") is True
    with open(crypttab_path, "r") as f:
        content = f.read()
    assert content.count("tpm2-device=") == 1

    # Unknown mapper returns False
    assert main.update_crypttab(tmpdir, "nonexistent", "auto") is False


# --- run() integration tests ---


def reset_global_storage():
    libcalamares.globalstorage = libcalamares.GlobalStorage(None)
    return libcalamares.globalstorage


# Non-UKI bootloader: skip
gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "grub")
assert main.run() is None

# Explicit opt-out: skip
gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("tpmAutoEnroll", False)
assert main.run() is None

# No encrypted root: skip, GS not written
gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert("tpmAutoEnroll", True)
assert main.run() is None
assert not gs.contains("tpmAutoEnrollPcrs")

# No TPM: error
gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert(
    "partitions",
    [
        {
            "mountPoint": "/",
            "device": "/dev/vda2",
            "luksMapperName": "cryptroot",
            "luksPassphrase": "secret",
        }
    ],
)
old_host_has_tpm = main.host_has_tpm
try:
    main.host_has_tpm = lambda: False
    error = main.run()
    assert error[0] == "TPM Configuration Error"
finally:
    main.host_has_tpm = old_host_has_tpm

# Successful two-phase enrollment: enroll + crypttab + first-boot service
gs = reset_global_storage()
gs.insert("packagechooser_bootloader", "systemd-boot-uki")
gs.insert(
    "partitions",
    [
        {
            "mountPoint": "/",
            "device": "/dev/vda2",
            "luksMapperName": "cryptroot",
            "luksPassphrase": "secret",
            "luksUuid": "test-uuid-1234",
        }
    ],
)

with tempfile.TemporaryDirectory() as tmpdir:
    os.makedirs(os.path.join(tmpdir, "etc"))
    crypttab_path = os.path.join(tmpdir, "etc", "crypttab")
    with open(crypttab_path, "w") as f:
        f.write("# /etc/crypttab\n")
        f.write(
            "cryptroot             UUID=test-uuid-1234"
            "                    none luks\n"
        )
    gs.insert("rootMountPoint", tmpdir)

    systemctl_calls = []
    old_host_has_tpm = main.host_has_tpm
    old_enroll_tpm2 = main.enroll_tpm2
    old_check_target = main.check_target_env_call
    try:
        main.host_has_tpm = lambda: True
        main.enroll_tpm2 = lambda device, passphrase, tpm2_device: (
            main.build_enroll_command(device, tpm2_device),
            types.SimpleNamespace(returncode=0, stdout="", stderr=""),
        )
        main.check_target_env_call = lambda cmd: systemctl_calls.append(cmd)

        assert main.run() is None

        # GS updated after successful enrollment
        assert gs.value("tpmAutoEnroll") is True
        assert gs.value("tpmAutoEnrollPcrs") == "11"

        # crypttab updated with tpm2-device=auto
        with open(crypttab_path, "r") as f:
            assert "tpm2-device=auto" in f.read()

        # Re-enroll script written with stable UUID-based device path
        script_path = tmpdir + main.REENROLL_SCRIPT_PATH
        assert os.path.exists(script_path)
        assert os.stat(script_path).st_mode & stat.S_IXUSR
        with open(script_path, "r") as f:
            script_content = f.read()
        assert "/dev/disk/by-uuid/test-uuid-1234" in script_content
        assert "--tpm2-pcrs=11" in script_content
        assert "--wipe-slot=tpm2" in script_content
        assert "--unlock-tpm2-device=auto" in script_content

        # Service unit written
        service_path = os.path.join(
            tmpdir, "etc", "systemd", "system", main.REENROLL_SERVICE_NAME
        )
        assert os.path.exists(service_path)

        # systemctl enable was called
        assert len(systemctl_calls) == 1
        assert "enable" in systemctl_calls[0]
        assert main.REENROLL_SERVICE_NAME in systemctl_calls[0]
    finally:
        main.host_has_tpm = old_host_has_tpm
        main.enroll_tpm2 = old_enroll_tpm2
        main.check_target_env_call = old_check_target
