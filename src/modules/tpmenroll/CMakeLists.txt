# SPDX-FileCopyrightText: no
# SPDX-License-Identifier: CC0-1.0

calamares_add_plugin(tpmenroll
    TYPE job
    EXPORT_MACRO PLUGINDLLEXPORT_PRO
    SOURCES
        TpmEnrollJob.cpp
    LINK_PRIVATE_LIBRARIES
        ${kfname}::CoreAddons
    SHARED_LIB
)
