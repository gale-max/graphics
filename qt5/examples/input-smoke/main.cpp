/* Exercise real QPA input and event-loop timers, without synthesizing Qt events. */
#include <QApplication>
#include <QKeyEvent>
#include <QMouseEvent>
#include <QPainter>
#include <QTimer>
#include <QWidget>
#include <cstdio>

class InputWindow : public QWidget
{
public:
    int keys = 0;
    int clicks = 0;
    int ticks = 0;

    InputWindow()
    {
        setFocusPolicy(Qt::StrongFocus);
        QTimer *timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, [this]() {
            ++ticks;
            update();
        });
        timer->start(1000);
    }

protected:
    void paintEvent(QPaintEvent *) override
    {
        QPainter painter(this);
        painter.fillRect(rect(), QColor(24, 38, 52));
        painter.setPen(Qt::white);
        QFont font = painter.font();
        font.setPixelSize(32);
        painter.setFont(font);
        painter.drawText(rect(), Qt::AlignCenter,
            QStringLiteral("Qt input: press A, B; click; press Enter\nkeys=%1 mouse=%2 timer=%3")
                .arg(keys).arg(clicks).arg(ticks));
    }

    void keyPressEvent(QKeyEvent *event) override
    {
        if ((keys == 0 && event->key() == Qt::Key_A) ||
            (keys == 1 && event->key() == Qt::Key_B))
            ++keys;
        std::printf("qt input key=%d keys=%d\n", event->key(), keys);
        std::fflush(stdout);
        update();
        if (event->key() == Qt::Key_Return) {
            bool pass = keys == 2 && clicks > 0 && ticks > 0;
            std::printf("qt input %s keys=%d mouse=%d timer=%d\n",
                        pass ? "pass" : "fail", keys, clicks, ticks);
            std::fflush(stdout);
            QApplication::exit(pass ? 0 : 1);
        }
    }

    void mousePressEvent(QMouseEvent *event) override
    {
        if (event->button() == Qt::LeftButton)
            ++clicks;
        std::printf("qt input mouse=%d x=%d y=%d\n", clicks, event->x(), event->y());
        std::fflush(stdout);
        update();
    }
};

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    InputWindow window;
    window.showFullScreen();
    QTimer::singleShot(90000, &app, [&app]() {
        std::puts("qt input fail timeout");
        std::fflush(stdout);
        app.exit(2);
    });
    return app.exec();
}
