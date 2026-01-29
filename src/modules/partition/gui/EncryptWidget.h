/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2016 Teo Mrnjavac <teo@kde.org>
 *   SPDX-FileCopyrightText: 2020 Adriaan de Groot <groot@kde.org>
 *   SPDX-FileCopyrightText: 2023 Evan James <dalto@fastmail.com>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */


#ifndef ENCRYPTWIDGET_H
#define ENCRYPTWIDGET_H

#include "compat/CheckBox.h"

#include <QWidget>

#include <kpmcore/fs/filesystem.h>

namespace Ui
{
class EncryptWidget;
}  // namespace Ui

class EncryptWidget : public QWidget
{
    Q_OBJECT

public:
    enum class Encryption : unsigned short
    {
        Disabled = 0,
        Unconfirmed,
        Confirmed
    };

    enum class TpmState : unsigned short
    {
        Unavailable = 0,  // No TPM detected on system
        Disabled,         // TPM available but not selected
        Enabled           // TPM auto-unlock enabled
    };

    explicit EncryptWidget( QWidget* parent = nullptr );

    void setEncryptionCheckbox( bool preCheckEncrypt = false );
    void reset( bool checkVisible = true );

    bool isEncryptionCheckboxChecked();
    Encryption state() const;
    void setText( const QString& text );

    /**
     * @brief setFilesystem sets the filesystem name used for password validation
     * @param fs A QString containing the name of the filesystem
     */
    void setFilesystem( const FileSystem::Type fs );

    QString passphrase() const;

    void retranslate();

    /// @brief Set whether the TPM checkbox should be visible
    void setTpmCheckboxVisible( bool visible );
    /// @brief Set whether the TPM checkbox should be enabled (can be toggled)
    void setTpmCheckboxEnabled( bool enabled );
    /// @brief Returns true if TPM auto-unlock is enabled
    bool isTpmEnabled() const;
    /// @brief Returns the current TPM state
    TpmState tpmState() const;
    /// @brief Check if TPM2 is available on this system
    static bool isTpmAvailable();

signals:
    void stateChanged( Encryption );
    void tpmStateChanged( TpmState );

private:
    void updateState( const bool notify = true );
    void onPassphraseEdited();
    void onCheckBoxStateChanged( Calamares::checkBoxStateType checked );

    Ui::EncryptWidget* m_ui;
    Encryption m_state;
    TpmState m_tpmState;

    FileSystem::Type m_filesystem;

    void onTpmCheckBoxStateChanged( Calamares::checkBoxStateType checked );
    void updateTpmState();
};

#endif  // ENCRYPTWIDGET_H
