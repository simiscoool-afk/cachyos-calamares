/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014 Aurélien Gâteau <agateau@kde.org>
 *   SPDX-FileCopyrightText: 2014 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2019 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */
#include "DeviceModel.h"

#include "core/SizeUtils.h"

#include "utils/Gui.h"
#include "partition/PartitionIterator.h"
#include "partition/PartitionQuery.h"

// KPMcore
#include <kpmcore/core/device.h>

#include <QIcon>
#include <QStandardItemModel>

// STL
#include <algorithm>

using Calamares::Partition::isOsproberEntryForDevice;
using Calamares::Partition::isPartitionFreeSpace;
using Calamares::Partition::PartitionIterator;

static void
sortDevices( DeviceModel::DeviceList& l )
{
    std::sort( l.begin(),
               l.end(),
               []( const Device* dev1, const Device* dev2 ) { return dev1->deviceNode() < dev2->deviceNode(); } );
}

DeviceModel::DeviceModel( QObject* parent )
    : QAbstractListModel( parent )
{
}

DeviceModel::~DeviceModel() {}

void
DeviceModel::init( const DeviceList& devices )
{
    beginResetModel();
    m_devices = devices;
    sortDevices( m_devices );
    endResetModel();
}

void
DeviceModel::setOsproberEntries( const OsproberEntryList& entries )
{
    m_osproberEntries = entries;
    updateDeviceStatuses();

    if ( rowCount() > 0 )
    {
        Q_EMIT dataChanged( index( 0 ), index( rowCount() - 1 ) );
    }
}

int
DeviceModel::rowCount( const QModelIndex& parent ) const
{
    return parent.isValid() ? 0 : m_devices.count();
}

QString
DeviceModel::makeStatusLabel( bool hasExistingPartitions, int osCount, const QString& osPrettyName ) const
{
    if ( osCount == 1 )
    {
        if ( !osPrettyName.isEmpty() )
        {
            return tr( "OS: %1", "@info:status storage device" ).arg( osPrettyName );
        }

        return tr( "OS detected", "@info:status storage device" );
    }
    if ( osCount > 1 )
    {
        return tr( "%1 OSes detected", "@info:status storage device" ).arg( osCount );
    }

    if ( hasExistingPartitions )
    {
        return tr( "No OS detected, has existing partitions", "@info:status storage device" );
    }

    return tr( "No OS detected, no partitions shown", "@info:status storage device" );
}

void
DeviceModel::updateDeviceStatuses()
{
    m_statusLabels.clear();
    m_statusLabels.reserve( m_devices.count() );

    for ( Device* device : std::as_const( m_devices ) )
    {
        bool hasExistingPartitions = false;
        for ( auto it = PartitionIterator::begin( device ); it != PartitionIterator::end( device ); ++it )
        {
            if ( !isPartitionFreeSpace( *it ) )
            {
                hasExistingPartitions = true;
                break;
            }
        }

        int osCount = 0;
        QString osPrettyName;
        for ( const auto& entry : m_osproberEntries )
        {
            if ( isOsproberEntryForDevice( entry, device ) )
            {
                ++osCount;
                if ( osCount == 1 )
                {
                    osPrettyName = entry.prettyName;
                }
            }
        }

        m_statusLabels.append( makeStatusLabel( hasExistingPartitions, osCount, osPrettyName ) );
    }
}

QVariant
DeviceModel::data( const QModelIndex& index, int role ) const
{
    int row = index.row();
    if ( row < 0 || row >= m_devices.count() )
    {
        return QVariant();
    }

    Device* device = m_devices.at( row );

    switch ( role )
    {
    case Qt::DisplayRole:
    case Qt::ToolTipRole:
    {
        const QString statusLabel = row < m_statusLabels.count() ? m_statusLabels.at( row ) : QString();
        if ( device->name().isEmpty() )
        {
            return tr( "%1 - %2", "@item storage device and status" ).arg( device->deviceNode(), statusLabel );
        }
        else
        {
            if ( device->logicalSize() >= 0 && device->totalLogical() >= 0 )
            {
                //: device[name] - size[number] (device-node[name]) - status[text]
                return tr( "%1 - %2 (%3) - %4", "@item storage device" )
                    .arg( device->name() )
                    .arg( formatByteSize( device->capacity() ) )
                    .arg( device->deviceNode() )
                    .arg( statusLabel );
            }
            else
            {
                // Newly LVM VGs don't have capacity property yet (i.e.
                // always has 1B capacity), so don't show it for a while.
                //
                //: device[name] - (device-node[name]) - status[text]
                return tr( "%1 - (%2) - %3", "@item storage device" )
                    .arg( device->name() )
                    .arg( device->deviceNode() )
                    .arg( statusLabel );
            }
        }
    }
    case Qt::DecorationRole:
        return Calamares::defaultPixmap(
            Calamares::PartitionDisk,
            Calamares::Original,
            QSize( Calamares::defaultIconSize().width() * 2, Calamares::defaultIconSize().height() * 2 ) );
    default:
        return QVariant();
    }
}

Device*
DeviceModel::deviceForIndex( const QModelIndex& index ) const
{
    int row = index.row();
    if ( row < 0 || row >= m_devices.count() )
    {
        return nullptr;
    }
    return m_devices.at( row );
}

void
DeviceModel::swapDevice( Device* oldDevice, Device* newDevice )
{
    Q_ASSERT( oldDevice );
    Q_ASSERT( newDevice );

    int indexOfOldDevice = m_devices.indexOf( oldDevice );
    if ( indexOfOldDevice < 0 )
    {
        return;
    }

    m_devices[ indexOfOldDevice ] = newDevice;
    updateDeviceStatuses();

    Q_EMIT dataChanged( index( indexOfOldDevice ), index( indexOfOldDevice ) );
}

void
DeviceModel::addDevice( Device* device )
{
    beginResetModel();
    m_devices << device;
    sortDevices( m_devices );
    updateDeviceStatuses();
    endResetModel();
}

void
DeviceModel::removeDevice( Device* device )
{
    beginResetModel();
    m_devices.removeAll( device );
    sortDevices( m_devices );
    updateDeviceStatuses();
    endResetModel();
}
