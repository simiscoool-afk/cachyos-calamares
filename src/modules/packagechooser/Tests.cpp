/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2019 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "Tests.h"

#ifdef HAVE_APPDATA
#include "ItemAppData.h"
#endif
#ifdef HAVE_APPSTREAM_VERSION
#include "ItemAppStream.h"
#endif
#include "Config.h"
#include "PackageModel.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"

#include <QtTest/QtTest>

QTEST_GUILESS_MAIN( PackageChooserTests )

PackageChooserTests::PackageChooserTests() {}

PackageChooserTests::~PackageChooserTests() {}

void
PackageChooserTests::initTestCase()
{
    Logger::setupLogLevel( Logger::LOGDEBUG );
    if ( !Calamares::JobQueue::instance() )
    {
        (void)new Calamares::JobQueue();
    }
}

void
PackageChooserTests::testBogus()
{
    QVERIFY( true );
}

void
PackageChooserTests::testAppData()
{
    // Path from the build-dir and from the running-the-test varies,
    // for in-source build, for build/, and for tests-in-build/,
    // so look in multiple places.
    QString appdataName( "io.calamares.calamares.appdata.xml" );
    for ( const auto& prefix : QStringList { "", "../", "../../../", "../../../../" } )
    {
        if ( QFile::exists( prefix + appdataName ) )
        {
            appdataName = prefix + appdataName;
            break;
        }
    }
    QVERIFY( QFile::exists( appdataName ) );

    QVariantMap m;
    m.insert( "appdata", appdataName );

#ifdef HAVE_XML
    PackageItem p1 = fromAppData( m );
    QVERIFY( p1.isValid() );
    QCOMPARE( p1.id, QStringLiteral( "io.calamares.calamares.desktop" ) );
    QCOMPARE( p1.name.get(), QStringLiteral( "Calamares" ) );
    // The <description> entry has precedence
    QCOMPARE( p1.description.get(), QStringLiteral( "Calamares is an installer program for Linux distributions." ) );
    // .. but en_GB doesn't have an entry in description, so uses <summary>
    QCOMPARE( p1.description.get( QLocale( "en_GB" ) ), QStringLiteral( "Calamares Linux Installer" ) );
    QCOMPARE( p1.description.get( QLocale( "nl" ) ),
              QStringLiteral( "Calamares is een installatieprogramma voor Linux distributies." ) );
    QVERIFY( p1.screenshotPath.isEmpty() );

    m.insert( "id", "calamares" );
    m.insert( "screenshot", ":/images/calamares.png" );
    PackageItem p2 = fromAppData( m );
    QVERIFY( p2.isValid() );
    QCOMPARE( p2.id, QStringLiteral( "calamares" ) );
    QCOMPARE( p2.description.get( QLocale( "nl" ) ),
              QStringLiteral( "Calamares is een installatieprogramma voor Linux distributies." ) );
    QVERIFY( !p2.screenshotPath.isEmpty() );
#endif
}

void
PackageChooserTests::testSystemRequirements()
{
    QVariantMap item;

    QVERIFY( itemMatchesSystemRequirements( item, false, false ) );

    item.insert( "efiOnly", true );
    QVERIFY( !itemMatchesSystemRequirements( item, false, false ) );
    QVERIFY( itemMatchesSystemRequirements( item, true, false ) );

    item.insert( "tpmRequired", true );
    QVERIFY( !itemMatchesSystemRequirements( item, true, false ) );
    QVERIFY( itemMatchesSystemRequirements( item, true, true ) );

    item.remove( "efiOnly" );
    QVERIFY( !itemMatchesSystemRequirements( item, false, false ) );
    QVERIFY( itemMatchesSystemRequirements( item, false, true ) );
}

void
PackageChooserTests::testBootloaderSelectionTpmState()
{
    auto* gs = Calamares::JobQueue::instanceGlobalStorage();
    QVERIFY( gs );

    gs->remove( QStringLiteral( "packagechooser_bootloader" ) );
    gs->remove( QStringLiteral( "tpmAutoEnroll" ) );
    gs->remove( QStringLiteral( "tpmAutoEnrollPcrs" ) );

    Config c;
    c.setDefaultId( Calamares::ModuleSystem::InstanceKey( QStringLiteral( "packagechooser" ),
                                                          QStringLiteral( "bootloader" ) ) );

    c.updateGlobalStorage( { QStringLiteral( "systemd-boot-uki" ) } );
    QCOMPARE( gs->value( QStringLiteral( "packagechooser_bootloader" ) ).toString(),
              QStringLiteral( "systemd-boot-uki" ) );
    QVERIFY( gs->value( QStringLiteral( "tpmAutoEnroll" ) ).toBool() );
    QCOMPARE( gs->value( QStringLiteral( "tpmAutoEnrollPcrs" ) ).toString(), QStringLiteral( "11" ) );

    gs->insert( QStringLiteral( "tpmAutoEnrollPcrs" ), QStringLiteral( "4" ) );
    c.updateGlobalStorage( { QStringLiteral( "systemd-boot-uki" ) } );
    QCOMPARE( gs->value( QStringLiteral( "tpmAutoEnrollPcrs" ) ).toString(), QStringLiteral( "4" ) );

    c.updateGlobalStorage( { QStringLiteral( "grub" ) } );
    QCOMPARE( gs->value( QStringLiteral( "packagechooser_bootloader" ) ).toString(), QStringLiteral( "grub" ) );
    QVERIFY( !gs->value( QStringLiteral( "tpmAutoEnroll" ) ).toBool() );
    QVERIFY( !gs->contains( QStringLiteral( "tpmAutoEnrollPcrs" ) ) );
}
