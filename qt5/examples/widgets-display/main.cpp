#include <QApplication>
#include <QCheckBox>
#include <QLabel>
#include <QLineEdit>
#include <QPalette>
#include <QVBoxLayout>
#include <QWidget>

int main(int argc, char *argv[])
{
    QApplication application(argc, argv);
    QWidget window;
    QVBoxLayout *layout = new QVBoxLayout(&window);
    QLabel *title = new QLabel(QStringLiteral("Qt Widgets Display Test"));
    QLineEdit *textBox = new QLineEdit(QStringLiteral("Textbox rendering is ready"));
    QCheckBox *checkBox = new QCheckBox(QStringLiteral("Checkbox rendering is ready"));
    QPalette palette = window.palette();

    palette.setColor(QPalette::Window, QColor(238, 244, 250));
    palette.setColor(QPalette::WindowText, QColor(24, 38, 52));
    window.setPalette(palette);
    window.setAutoFillBackground(true);

    title->setAlignment(Qt::AlignCenter);
    title->setStyleSheet(QStringLiteral("font-size: 34px; font-weight: bold;"));
    textBox->setReadOnly(true);
    textBox->setMinimumHeight(64);
    textBox->setStyleSheet(QStringLiteral("font-size: 24px; padding: 8px;"));
    checkBox->setChecked(true);
    checkBox->setStyleSheet(QStringLiteral("font-size: 24px; spacing: 12px;"));

    layout->setContentsMargins(120, 100, 120, 100);
    layout->setSpacing(36);
    layout->addStretch();
    layout->addWidget(title);
    layout->addWidget(textBox);
    layout->addWidget(checkBox, 0, Qt::AlignHCenter);
    layout->addStretch();

    window.showFullScreen();
    return application.exec();
}
