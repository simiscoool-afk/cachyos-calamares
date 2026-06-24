/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2014 Aurélien Gâteau <agateau@kde.org>
 *   SPDX-FileCopyrightText: 2017 2019, Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */
#ifndef DEVICEMODEL_H
#define DEVICEMODEL_H

#include <QAbstractListModel>
#include <QList>
#include <QScopedPointer>
#include <QVector>

#include "core/OsproberEntry.h"

class Device;
class PartitionModel;

/**
 * A Qt model which exposes a list of Devices.
 */
class DeviceModel : public QAbstractListModel
{
    Q_OBJECT
public:
    DeviceModel( QObject* parent = nullptr );
    ~DeviceModel() override;

    using DeviceList = QList< Device* >;

    /**
     * Init the model with the list of devices. Does *not* take ownership of the
     * devices.
     */
    void init( const DeviceList& devices );
    void setOsproberEntries( const OsproberEntryList& entries );

    int rowCount( const QModelIndex& parent = QModelIndex() ) const override;
    QVariant data( const QModelIndex& index, int role = Qt::DisplayRole ) const override;

    Device* deviceForIndex( const QModelIndex& index ) const;

    void swapDevice( Device* oldDevice, Device* newDevice );

    void addDevice( Device* device );

    void removeDevice( Device* device );

private:
    QString makeStatusLabel( bool hasExistingPartitions, int osCount, const QString& osPrettyName ) const;
    void updateDeviceStatuses();

    DeviceList m_devices;
    OsproberEntryList m_osproberEntries;
    QVector< QString > m_statusLabels;
};

#endif /* DEVICEMODEL_H */
