/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2015-2016 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2018-2019, 2024 Adriaan de Groot <groot@kde.org>
 *   SPDX-FileCopyrightText: 2019 Collabora Ltd <arnaud.ferraris@collabora.com>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "OsproberEntry.h"

#include <kpmcore/core/device.h>

#include <QtGlobal>

bool
FstabEntry::isValid() const
{
    return !partitionNode.isEmpty() && !mountPoint.isEmpty() && !fsType.isEmpty();
}

FstabEntry
FstabEntry::fromEtcFstab( const QString& rawLine )
{
    QString line = rawLine.simplified();
    if ( line.startsWith( '#' ) )
    {
        return FstabEntry { QString(), QString(), QString(), QString(), 0, 0 };
    }

    QStringList splitLine = line.split( ' ' );
    if ( splitLine.length() != 6 )
    {
        return FstabEntry { QString(), QString(), QString(), QString(), 0, 0 };
    }

    return FstabEntry {
        splitLine.at( 0 ),  // path, or UUID, or LABEL, etc.
        splitLine.at( 1 ),  // mount point
        splitLine.at( 2 ),  // fs type
        splitLine.at( 3 ),  // options
        splitLine.at( 4 ).toInt(),  //dump
        splitLine.at( 5 ).toInt()  //pass
    };
}

namespace Calamares
{
FstabEntryList
fromEtcFstabContents( const QStringList& fstabLines )
{
    FstabEntryList fstabEntries;

    for ( const QString& rawLine : fstabLines )
    {
        fstabEntries.append( FstabEntry::fromEtcFstab( rawLine ) );
    }
    const auto invalidEntries = std::remove_if(
        fstabEntries.begin(), fstabEntries.end(), []( const FstabEntry& x ) { return !x.isValid(); } );
    fstabEntries.erase( invalidEntries, fstabEntries.end() );
    return fstabEntries;
}

}  // namespace Calamares

namespace Calamares::Partition
{
static bool
isPartitionPathOnDevice( const QString& partitionPath, const QString& deviceNode )
{
    if ( partitionPath.isEmpty() || deviceNode.isEmpty() || !partitionPath.startsWith( deviceNode ) )
    {
        return false;
    }

    if ( partitionPath.length() == deviceNode.length() )
    {
        return true;
    }

    const auto next = partitionPath.at( deviceNode.length() );
    return next.isDigit() || next == QLatin1Char( 'p' );
}

bool
isOsproberEntryForDevice( const OsproberEntry& entry, Device* device )
{
    Q_ASSERT( device );
    return isPartitionPathOnDevice( entry.path, device->deviceNode() );
}

OsproberEntryList
osproberEntriesForDevice( const OsproberEntryList& entries, Device* device )
{
    OsproberEntryList deviceEntries;
    for ( const auto& entry : entries )
    {
        if ( isOsproberEntryForDevice( entry, device ) )
        {
            deviceEntries.append( entry );
        }
    }
    return deviceEntries;
}

}  // namespace Calamares::Partition
