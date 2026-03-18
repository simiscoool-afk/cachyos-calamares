/* QML navigation for CachyOS Calamares.

   SPDX-FileCopyrightText: 2020 Adriaan de Groot <groot@kde.org>
   SPDX-FileCopyrightText: 2024 CachyOS team
   SPDX-License-Identifier: GPL-3.0-or-later

   The navigation panel provides Back/Next/Quit buttons styled
   to match the CachyOS sidebar theme.
*/
import io.calamares.ui 1.0
import io.calamares.core 1.0

import QtQuick 2.3
import QtQuick.Controls 2.10
import QtQuick.Layouts 1.3

Rectangle {
    id: navigationBar;
    color: Branding.styleString( Branding.SidebarBackground );
    height: 48;

    RowLayout {
        id: buttonBar
        anchors.fill: parent;
        spacing: 10;

        Item {
            Layout.fillWidth: true;
        }

        Button {
            id: backButton;
            text: ViewManager.backLabel;
            icon.name: ViewManager.backIcon;

            enabled: ViewManager.backEnabled;
            visible: ViewManager.backAndNextVisible;
            onClicked: { ViewManager.back(); }

            palette.buttonText: "#FFFFFF";
            palette.button: "#292F34";

            background: Rectangle {
                implicitWidth: 100;
                implicitHeight: 36;
                color: backButton.hovered ? "#3A4248" : "#292F34";
                border.color: "#00CED1";
                border.width: 1;
                radius: 4;
            }
        }

        Button {
            id: nextButton;
            text: ViewManager.nextLabel;
            icon.name: ViewManager.nextIcon;

            enabled: ViewManager.nextEnabled;
            visible: ViewManager.backAndNextVisible;
            onClicked: { ViewManager.next(); }

            Layout.rightMargin: 3 * buttonBar.spacing;

            palette.buttonText: "#292F34";
            palette.button: "#00CED1";

            background: Rectangle {
                implicitWidth: 100;
                implicitHeight: 36;
                color: nextButton.enabled ? (nextButton.hovered ? "#00E5E8" : "#00CED1") : "#555555";
                radius: 4;
            }

            contentItem: Text {
                text: nextButton.text;
                color: nextButton.enabled ? "#292F34" : "#888888";
                horizontalAlignment: Text.AlignHCenter;
                verticalAlignment: Text.AlignVCenter;
                font.weight: Font.Bold;
            }
        }

        Button {
            id: quitButton;
            Layout.rightMargin: 2 * buttonBar.spacing;
            text: ViewManager.quitLabel;
            icon.name: ViewManager.quitIcon;

            ToolTip.visible: hovered;
            ToolTip.timeout: 5000;
            ToolTip.delay: 1000;
            ToolTip.text: ViewManager.quitTooltip;

            enabled: ViewManager.quitEnabled;
            visible: ViewManager.quitVisible;
            onClicked: { ViewManager.quit(); }

            palette.buttonText: "#FFFFFF";
            palette.button: "#292F34";

            background: Rectangle {
                implicitWidth: 100;
                implicitHeight: 36;
                color: quitButton.hovered ? "#3A4248" : "#292F34";
                border.color: "#555555";
                border.width: 1;
                radius: 4;
            }
        }
    }
}
