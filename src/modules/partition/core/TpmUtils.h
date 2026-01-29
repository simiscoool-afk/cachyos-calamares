/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2026 CachyOS Team
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#ifndef TPMUTILS_H
#define TPMUTILS_H

#include <QString>

namespace TpmUtils
{

/**
 * @brief Check if a TPM2 device is available on this system
 *
 * Checks for the presence of /sys/class/tpm/tpm0 and verifies
 * that the TPM supports TPM 2.0 (required for systemd-cryptenroll).
 *
 * @return true if TPM2 is available and usable, false otherwise
 */
bool isTpm2Available();

/**
 * @brief Get a human-readable description of the TPM status
 *
 * @return QString describing the TPM status (e.g., "TPM 2.0 available" or "No TPM detected")
 */
QString tpmStatusDescription();

}  // namespace TpmUtils

#endif  // TPMUTILS_H
