# SPDX-FileCopyrightText: no
# SPDX-License-Identifier: CC0-1.0
#
# Calamares Boilerplate
import libcalamares
libcalamares.globalstorage = libcalamares.GlobalStorage(None)
libcalamares.globalstorage.insert("testing", True)


class Job(object):
    def __init__(self):
        self.configuration = {
            "loaderEntries": ["timeout 3", "console-mode keep"],
            "kernelParams": ["quiet"],
        }


libcalamares.job = Job()

# Module prep-work
from src.modules.bootloader import main

# Specific Bootloader test
g = main.get_efi_suffix_generator("derp${SERIAL}")
assert g is not None
assert g.next() == "derp"  # First time, no suffix
for n in range(9):
    print(g.next())
# We called next() 10 times in total, starting from 0
assert g.next() == "derp10"

g = main.get_efi_suffix_generator("derp${RANDOM}")
assert g is not None
for n in range(10):
    print(g.next())
# it's random, nothing to assert

g = main.get_efi_suffix_generator("derp${PHRASE}")
assert g is not None
for n in range(10):
    print(g.next())
# it's random, nothing to assert

# Check invalid things
try:
    g = main.get_efi_suffix_generator("derp")
    raise TypeError("Shouldn't get generator (no indicator)")
except ValueError as e:
    pass

try:
    g = main.get_efi_suffix_generator("derp${HEX}")
    raise TypeError("Shouldn't get generator (unknown indicator)")
except ValueError as e:
    pass

try:
    g = main.get_efi_suffix_generator("derp${SERIAL}x")
    raise TypeError("Shouldn't get generator (trailing garbage)")
except ValueError as e:
    pass

try:
    g = main.get_efi_suffix_generator("derp${SERIAL}${RANDOM}")
    raise TypeError("Shouldn't get generator (multiple indicators)")
except ValueError as e:
    pass


# Try the generator (assuming no calamares- test files exist in /tmp)
import os
assert "calamares-single" == main.change_efi_suffix("/tmp", "calamares-single")
assert "calamares-serial" == main.change_efi_suffix("/tmp", "calamares-serial${SERIAL}")
try:
    os.makedirs("/tmp/calamares-serial", exist_ok=True)
    assert "calamares-serial1" == main.change_efi_suffix("/tmp", "calamares-serial${SERIAL}")
finally:
    os.rmdir("/tmp/calamares-serial")


import stat
import tempfile

with tempfile.TemporaryDirectory(prefix="calamares-systemd-boot-uki") as tempdir:
    os.makedirs(tempdir + "/etc")
    os.makedirs(tempdir + "/boot/loader")
    with open(tempdir + "/etc/machine-id", "w") as f:
        f.write("0123456789abcdef0123456789abcdef\n")

    old_get_kernel_params = main.get_kernel_params
    try:
        main.get_kernel_params = lambda uuid: ["quiet", "rw", f"root=UUID={uuid}"]
        main.write_systemd_boot_uki_config(tempdir, "root-uuid")
    finally:
        main.get_kernel_params = old_get_kernel_params

    with open(tempdir + "/etc/kernel/cmdline", "r") as f:
        assert f.read() == "quiet rw root=UUID=root-uuid\n"
    with open(tempdir + "/etc/kernel/entry-token", "r") as f:
        assert f.read() == "0123456789abcdef0123456789abcdef\n"
    with open(tempdir + "/etc/kernel/install.conf", "r") as f:
        assert "layout=uki" in f.read()
    with open(tempdir + "/etc/kernel/uki.conf", "r") as f:
        assert f.read() == "[UKI]\n"

    main.create_loader(tempdir + "/boot/loader/loader.conf", tempdir)
    with open(tempdir + "/boot/loader/loader.conf", "r") as f:
        assert f.read() == "default @saved\ntimeout 3\nconsole-mode keep\n"

    main.install_systemd_boot_uki_maintenance(tempdir)
    script_path = tempdir + main.UKI_MAINTENANCE_SCRIPT
    assert os.path.exists(script_path)
    assert os.stat(script_path).st_mode & stat.S_IXUSR
    with open(tempdir + main.UKI_KERNEL_UPDATE_HOOK, "r") as f:
        assert main.UKI_MAINTENANCE_SCRIPT + " add-all" in f.read()
    with open(tempdir + main.UKI_KERNEL_REMOVE_HOOK, "r") as f:
        assert main.UKI_MAINTENANCE_SCRIPT + " prune" in f.read()
    with open(tempdir + main.UKI_SYSTEMD_UPDATE_HOOK, "r") as f:
        assert main.UKI_MAINTENANCE_SCRIPT + " refresh" in f.read()
