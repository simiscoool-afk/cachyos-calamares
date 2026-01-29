/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2026 CachyOS Team
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "TpmUtils.h"

#include "utils/Logger.h"

#include <QDir>
#include <QFile>
#include <QProcess>
#include <QRegularExpression>

namespace TpmUtils
{

/**
 * @brief Check the TPM version from /sys/class/tpm/tpm0/tpm_version_major
 *
 * @return The major version number (2 for TPM 2.0), or 0 if not readable
 */
static int
getTpmMajorVersion()
{
    QFile versionFile( QStringLiteral( "/sys/class/tpm/tpm0/tpm_version_major" ) );
    if ( versionFile.open( QIODevice::ReadOnly | QIODevice::Text ) )
    {
        QString version = QString::fromUtf8( versionFile.readAll() ).trimmed();
        bool ok = false;
        int majorVersion = version.toInt( &ok );
        if ( ok )
        {
            return majorVersion;
        }
    }
    return 0;
}

/**
 * @brief Try to detect TPM version using tpm2_getcap if available
 *
 * This is a fallback method when sysfs doesn't provide version info.
 *
 * @return true if TPM2 tools can communicate with a TPM2 device
 */
static bool
checkTpm2WithTools()
{
    QProcess process;
    process.setProgram( QStringLiteral( "tpm2_getcap" ) );
    process.setArguments( { QStringLiteral( "properties-fixed" ) } );
    process.start();

    if ( !process.waitForFinished( 3000 ) )
    {
        return false;
    }

    // If the command succeeds, we have a working TPM2
    return process.exitCode() == 0;
}

bool
isTpm2Available()
{
    // First, check if the TPM device exists in sysfs
    QDir tpmDir( QStringLiteral( "/sys/class/tpm/tpm0" ) );
    if ( !tpmDir.exists() )
    {
        cDebug() << "TPM: No TPM device found at /sys/class/tpm/tpm0";
        return false;
    }

    // Check for TPM resource manager device (required for TPM2)
    QFile tpmrmDevice( QStringLiteral( "/dev/tpmrm0" ) );
    if ( !tpmrmDevice.exists() )
    {
        cDebug() << "TPM: No TPM resource manager device at /dev/tpmrm0";
        // Don't return false yet, might still work
    }

    // Try to get the TPM version from sysfs
    int majorVersion = getTpmMajorVersion();
    if ( majorVersion > 0 )
    {
        if ( majorVersion >= 2 )
        {
            cDebug() << "TPM: TPM 2.0 detected via sysfs";
            return true;
        }
        else
        {
            cDebug() << "TPM: TPM 1.x detected (not supported for auto-unlock)";
            return false;
        }
    }

    // Fallback: try using tpm2 tools
    if ( checkTpm2WithTools() )
    {
        cDebug() << "TPM: TPM 2.0 detected via tpm2_getcap";
        return true;
    }

    cDebug() << "TPM: Unable to detect TPM version or no TPM2 available";
    return false;
}

QString
tpmStatusDescription()
{
    QDir tpmDir( QStringLiteral( "/sys/class/tpm/tpm0" ) );
    if ( !tpmDir.exists() )
    {
        return QObject::tr( "No TPM detected" );
    }

    int majorVersion = getTpmMajorVersion();
    if ( majorVersion >= 2 )
    {
        return QObject::tr( "TPM 2.0 available" );
    }
    else if ( majorVersion == 1 )
    {
        return QObject::tr( "TPM 1.x detected (not supported)" );
    }

    // Try tools as fallback
    if ( checkTpm2WithTools() )
    {
        return QObject::tr( "TPM 2.0 available" );
    }

    return QObject::tr( "TPM detected but version unknown" );
}

}  // namespace TpmUtils
