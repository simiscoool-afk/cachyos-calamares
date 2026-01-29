/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2026 CachyOS Team
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "TpmEnrollJob.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"
#include "utils/String.h"
#include "utils/System.h"
#include "utils/Variant.h"

#include <QDir>
#include <QFile>

TpmEnrollJob::TpmEnrollJob( QObject* parent )
    : Calamares::CppJob( parent )
{
}

TpmEnrollJob::~TpmEnrollJob() {}

QString
TpmEnrollJob::prettyName() const
{
    return tr( "Enrolling TPM for disk encryption…", "@status" );
}

QString
TpmEnrollJob::prettyDescription() const
{
    return tr( "Configuring automatic disk unlock using TPM2.", "@info" );
}

QString
TpmEnrollJob::prettyStatusMessage() const
{
    return tr( "Enrolling TPM for automatic disk encryption unlock…", "@status" );
}

Calamares::JobResult
TpmEnrollJob::exec()
{
    Calamares::GlobalStorage* gs = Calamares::JobQueue::instance()->globalStorage();

    // Check if TPM encryption was requested
    bool useTpmEncryption = gs->value( "useTpmEncryption" ).toBool();
    if ( !useTpmEncryption )
    {
        cDebug() << "TPM encryption not requested, skipping enrollment";
        return Calamares::JobResult::ok();
    }

    // Get the LUKS passphrase (needed for enrollment)
    QString obscuredPassphrase = gs->value( "luksPassphrase" ).toString();
    if ( obscuredPassphrase.isEmpty() )
    {
        cDebug() << "No LUKS passphrase found, skipping TPM enrollment";
        return Calamares::JobResult::ok();
    }
    // Calamares::String::obscure is symmetric (XOR-based), so it decodes when applied again
    QString passphrase = Calamares::String::obscure( obscuredPassphrase );

    // Get the list of partitions
    QVariantList partitions = gs->value( "partitions" ).toList();
    if ( partitions.isEmpty() )
    {
        return Calamares::JobResult::error(
            tr( "TPM enrollment error", "@error" ),
            tr( "No partitions found for TPM enrollment.", "@error" ) );
    }

    // Find LUKS partitions to enroll
    int enrolledCount = 0;
    for ( const QVariant& partitionVariant : partitions )
    {
        QVariantMap partition = partitionVariant.toMap();

        // Check if this is a LUKS partition
        if ( !partition.contains( "luksMapperName" ) )
        {
            continue;
        }

        QString device = partition.value( "device" ).toString();
        if ( device.isEmpty() )
        {
            cWarning() << "LUKS partition has no device path, skipping";
            continue;
        }

        cDebug() << "Enrolling TPM for LUKS device:" << device;

        // Build systemd-cryptenroll command
        QStringList args;
        args << device;
        args << "--tpm2-device=auto";

        // Add PCR bindings if specified
        if ( !m_tpmPcrs.isEmpty() )
        {
            args << QString( "--tpm2-pcrs=%1" ).arg( m_tpmPcrs );
        }

        // Build the full command with systemd-cryptenroll
        QStringList command;
        command << QStringLiteral( "systemd-cryptenroll" ) << args;

        // Run systemd-cryptenroll in the target environment
        // We need to pass the passphrase via stdin
        auto result = Calamares::System::instance()->targetEnvCommand(
            command,
            QString(),  // working directory
            passphrase + "\n",  // stdin input (passphrase)
            std::chrono::seconds( 60 ) );

        if ( result.getExitCode() != 0 )
        {
            QString errorOutput = result.getOutput();
            cWarning() << "systemd-cryptenroll failed for" << device << ":" << errorOutput;

            // Don't fail the entire installation, just warn
            // TPM enrollment is optional - the user can still use the passphrase
            cWarning() << "TPM enrollment failed, continuing with passphrase-only encryption";
            continue;
        }

        cDebug() << "Successfully enrolled TPM for" << device;
        enrolledCount++;
    }

    if ( enrolledCount > 0 )
    {
        cDebug() << "TPM enrollment complete:" << enrolledCount << "partition(s) enrolled";
        gs->insert( "tpmEnrolled", true );
    }
    else
    {
        cDebug() << "No partitions were enrolled with TPM";
        gs->insert( "tpmEnrolled", false );
    }

    return Calamares::JobResult::ok();
}

void
TpmEnrollJob::setConfigurationMap( const QVariantMap& configurationMap )
{
    m_tpmPcrs = Calamares::getString( configurationMap, "tpmPcrs" );
}

CALAMARES_PLUGIN_FACTORY_DEFINITION( TpmEnrollJobFactory, registerPlugin< TpmEnrollJob >(); )
