/* QML sidebar for CachyOS Calamares.

   SPDX-FileCopyrightText: 2020 Adriaan de Groot <groot@kde.org>
   SPDX-FileCopyrightText: 2021 Anke Boersma <demm@kaosx.us>
   SPDX-FileCopyrightText: 2024 CachyOS team
   SPDX-License-Identifier: GPL-3.0-or-later

   Vertical left sidebar showing installation progress steps
   with CachyOS branding.
*/

import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Layouts 1.3
import QtQuick.Controls 2.15

Rectangle {
    id: sideBar
    color: Branding.styleString(Branding.SidebarBackground)
    width: 200

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Logo
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            Layout.topMargin: 8

            Image {
                id: logo
                anchors.centerIn: parent
                width: 48
                height: 48
                source: "file:/" + Branding.imagePath(Branding.ProductLogo)
                sourceSize.width: width
                sourceSize.height: height
            }
        }

        // Product name
        Text {
            Layout.fillWidth: true
            Layout.bottomMargin: 12
            text: Branding.string(Branding.ProductName)
            color: Branding.styleString(Branding.SidebarText)
            horizontalAlignment: Text.AlignHCenter
            font.pointSize: 14
            font.weight: Font.Bold
        }

        // Separator
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            Layout.bottomMargin: 12
            height: 1
            color: "#3A4248"
        }

        // Step list
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: stepsView
                anchors.fill: parent
                model: ViewManager
                interactive: contentHeight > height
                clip: true
                spacing: 2

                delegate: Item {
                    width: stepsView.width
                    height: 36

                    property bool isCurrent: index === ViewManager.currentStepIndex
                    property bool isCompleted: index < ViewManager.currentStepIndex

                    // Current step highlight
                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        height: parent.height
                        radius: 6
                        color: isCurrent
                            ? Branding.styleString(Branding.SidebarBackgroundCurrent)
                            : "transparent"
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 22
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10

                        // Step indicator dot
                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: isCurrent
                                ? Branding.styleString(Branding.SidebarTextCurrent)
                                : isCompleted
                                    ? Branding.styleString(Branding.SidebarBackgroundCurrent)
                                    : "#555555"
                            border.width: (!isCurrent && !isCompleted) ? 1 : 0
                            border.color: "#666666"
                        }

                        // Step name
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: display
                            color: isCurrent
                                ? Branding.styleString(Branding.SidebarTextCurrent)
                                : isCompleted
                                    ? Branding.styleString(Branding.SidebarBackgroundCurrent)
                                    : Branding.styleString(Branding.SidebarText)
                            font.pointSize: 10
                            font.weight: isCurrent ? Font.Bold : Font.Normal
                            opacity: (!isCurrent && !isCompleted) ? 0.7 : 1.0
                        }
                    }
                }
            }
        }

        // Version at bottom
        Text {
            Layout.fillWidth: true
            Layout.bottomMargin: 12
            Layout.topMargin: 8
            text: Branding.string(Branding.Version)
            color: Branding.styleString(Branding.SidebarText)
            horizontalAlignment: Text.AlignHCenter
            font.pointSize: 8
            opacity: 0.4
        }
    }
}
