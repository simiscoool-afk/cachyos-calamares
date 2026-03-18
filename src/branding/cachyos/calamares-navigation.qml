/* QML navigation for CachyOS Calamares.

   SPDX-FileCopyrightText: 2020 Adriaan de Groot <groot@kde.org>
   SPDX-FileCopyrightText: 2024 CachyOS team
   SPDX-License-Identifier: GPL-3.0-or-later

   Bottom navigation bar with Back / Next / Quit buttons
   styled to match CachyOS branding.
*/
import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.3

Rectangle {
    id: navigationBar
    color: Branding.styleString(Branding.SidebarBackground)
    height: 56

    // Subtle top border
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: "#3A4248"
    }

    RowLayout {
        id: buttonBar
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12

        // Quit on the left
        Button {
            id: quitButton
            text: ViewManager.quitLabel
            icon.name: ViewManager.quitIcon

            ToolTip.visible: hovered
            ToolTip.timeout: 5000
            ToolTip.delay: 1000
            ToolTip.text: ViewManager.quitTooltip

            enabled: ViewManager.quitEnabled
            visible: ViewManager.quitVisible
            onClicked: { ViewManager.quit(); }

            background: Rectangle {
                implicitWidth: 100
                implicitHeight: 38
                color: quitButton.hovered ? "#3A4248" : "transparent"
                border.color: "#555555"
                border.width: 1
                radius: 6
            }

            contentItem: Text {
                text: quitButton.text
                color: quitButton.enabled ? "#FFFFFF" : "#666666"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pointSize: 10
            }
        }

        Item {
            Layout.fillWidth: true
        }

        // Back
        Button {
            id: backButton
            text: ViewManager.backLabel
            icon.name: ViewManager.backIcon

            enabled: ViewManager.backEnabled
            visible: ViewManager.backAndNextVisible
            onClicked: { ViewManager.back(); }

            background: Rectangle {
                implicitWidth: 110
                implicitHeight: 38
                color: backButton.hovered ? "#3A4248" : "transparent"
                border.color: "#00CED1"
                border.width: 1
                radius: 6
            }

            contentItem: Text {
                text: backButton.text
                color: backButton.enabled ? "#FFFFFF" : "#666666"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pointSize: 10
            }
        }

        // Next (primary action)
        Button {
            id: nextButton
            text: ViewManager.nextLabel
            icon.name: ViewManager.nextIcon

            enabled: ViewManager.nextEnabled
            visible: ViewManager.backAndNextVisible
            onClicked: { ViewManager.next(); }

            background: Rectangle {
                implicitWidth: 110
                implicitHeight: 38
                color: nextButton.enabled
                    ? (nextButton.hovered ? "#00E5E8" : "#00CED1")
                    : "#3A4248"
                radius: 6
            }

            contentItem: Text {
                text: nextButton.text
                color: nextButton.enabled ? "#292F34" : "#666666"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pointSize: 10
                font.weight: Font.Bold
            }
        }
    }
}
