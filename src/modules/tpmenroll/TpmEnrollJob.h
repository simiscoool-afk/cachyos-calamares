/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2026 CachyOS Team
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#ifndef TPMENROLLJOB_H
#define TPMENROLLJOB_H

#include "CppJob.h"
#include "DllMacro.h"
#include "utils/PluginFactory.h"

#include <QObject>
#include <QVariantMap>

class PLUGINDLLEXPORT TpmEnrollJob : public Calamares::CppJob
{
    Q_OBJECT

public:
    explicit TpmEnrollJob( QObject* parent = nullptr );
    ~TpmEnrollJob() override;

    QString prettyName() const override;
    QString prettyDescription() const override;
    QString prettyStatusMessage() const override;

    Calamares::JobResult exec() override;

    void setConfigurationMap( const QVariantMap& configurationMap ) override;

private:
    QString m_tpmPcrs;
};

CALAMARES_PLUGIN_FACTORY_DECLARATION( TpmEnrollJobFactory )

#endif  // TPMENROLLJOB_H
