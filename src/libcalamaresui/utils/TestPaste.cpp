/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2021 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 *
 */

#include "Paste.h"
#include "network/Manager.h"

#include "utils/Logger.h"

#include <QDateTime>
#include <QNetworkReply>
#include <QTimer>
#include <QtTest/QtTest>

extern QByteArray logFileContents( qint64 sizeLimitBytes );
extern QString ficheLogUpload( const QByteArray& pasteData, const QUrl& serverUrl, QObject* parent );
extern QString httpPasteUrl( const QByteArray& responseText, const QUrl& serverUrl );
extern bool waitForReply( QNetworkReply* reply, int timeoutMs );

class FakeNetworkReply : public QNetworkReply
{
public:
    explicit FakeNetworkReply( QObject* parent = nullptr )
        : QNetworkReply( parent )
    {
        open( QIODevice::ReadOnly | QIODevice::Unbuffered );
        setOperation( QNetworkAccessManager::PostOperation );
        setUrl( QUrl( "https://paste.cachyos.org" ) );
    }

    void succeed( const QByteArray& data = QByteArray() )
    {
        m_data = data;
        m_offset = 0;
        setFinished( true );
        emit readyRead();
        emit finished();
    }

    bool aborted() const { return m_aborted; }

    void abort() override
    {
        m_aborted = true;
        setFinished( true );
        setError( QNetworkReply::OperationCanceledError, "timed out" );
        emit finished();
    }

    qint64 bytesAvailable() const override
    {
        return m_data.size() - m_offset + QIODevice::bytesAvailable();
    }

protected:
    qint64 readData( char* data, qint64 maxlen ) override
    {
        if ( m_offset >= m_data.size() )
        {
            return -1;
        }

        const qint64 len = qMin< qint64 >( maxlen, m_data.size() - m_offset );
        memcpy( data, m_data.constData() + m_offset, size_t( len ) );
        m_offset += len;
        return len;
    }

private:
    QByteArray m_data;
    qint64 m_offset = 0;
    bool m_aborted = false;
};

class TestPaste : public QObject
{
    Q_OBJECT

public:
    TestPaste() {}
    ~TestPaste() override {}

private Q_SLOTS:
    void testGetLogFile();
    void testHttpPasteUrl();
    void testWaitForReplyCompletes();
    void testWaitForReplyTimeout();
    void testFichePaste();
    void testUploadSize();
};

void
TestPaste::testGetLogFile()
{
    QFile::remove( Logger::logFile() );
    // This test assumes nothing **else** has set up logging yet
    QByteArray logLimitedBefore = logFileContents( 16 );
    QVERIFY( logLimitedBefore.isEmpty() );
    QByteArray logUnlimitedBefore = logFileContents( -1 );
    QVERIFY( logUnlimitedBefore.isEmpty() );

    Logger::setupLogLevel( Logger::LOGDEBUG );
    Logger::setupLogfile();

    QByteArray logLimitedAfter = logFileContents( 16 );
    QVERIFY( !logLimitedAfter.isEmpty() );
    QByteArray logUnlimitedAfter = logFileContents( -1 );
    QVERIFY( !logUnlimitedAfter.isEmpty() );
}

void
TestPaste::testHttpPasteUrl()
{
    QCOMPARE( httpPasteUrl( QByteArray( "/abc123\n" ), QUrl( "https://paste.cachyos.org" ) ),
              QString( "https://paste.cachyos.org/abc123.log" ) );
    QVERIFY( httpPasteUrl( QByteArray( "https://example.org/abc123\n" ), QUrl( "https://paste.cachyos.org" ) )
                 .isEmpty() );
}

void
TestPaste::testWaitForReplyCompletes()
{
    FakeNetworkReply reply;
    QTimer::singleShot( 0, &reply, [ &reply ]() { reply.succeed( QByteArray( "/abc123" ) ); } );

    QVERIFY( waitForReply( &reply, 100 ) );
    QVERIFY( !reply.aborted() );
}

void
TestPaste::testWaitForReplyTimeout()
{
    FakeNetworkReply reply;

    QVERIFY( !waitForReply( &reply, 10 ) );
    QVERIFY( reply.aborted() );
}

void
TestPaste::testFichePaste()
{
    QString blabla( "the quick brown fox tested Calamares and found it rubbery" );
    QDateTime now = QDateTime::currentDateTime();

    QByteArray d = ( blabla + now.toString() ).toUtf8();
    QString s = ficheLogUpload( d, QUrl( "http://termbin.com:9999" ), nullptr );

    cDebug() << "Paste data to" << s;
    QVERIFY( !s.isEmpty() );
}

void
TestPaste::testUploadSize()
{
    QByteArray logContent = logFileContents( 100 );
    QString s = ficheLogUpload( logContent, QUrl( "http://termbin.com:9999" ), nullptr );

    QVERIFY( !s.isEmpty() );

    QUrl url( s );
    QByteArray returnedData = Calamares::Network::Manager().synchronousGet( url );

    QCOMPARE( returnedData.size(), 100 );
}
QTEST_GUILESS_MAIN( TestPaste )

#include "utils/moc-warnings.h"

#include "TestPaste.moc"
