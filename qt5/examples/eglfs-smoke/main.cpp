#include <QGuiApplication>
#include <QOpenGLFunctions>
#include <QOpenGLWindow>
#include <QTimer>

class SmokeWindow final : public QOpenGLWindow, protected QOpenGLFunctions
{
protected:
    void initializeGL() override
    {
        initializeOpenGLFunctions();
        glClearColor(0.05F, 0.35F, 0.70F, 1.0F);
    }

    void paintGL() override
    {
        glClear(GL_COLOR_BUFFER_BIT);
    }
};

int main(int argc, char *argv[])
{
    QGuiApplication application(argc, argv);
    SmokeWindow window;
    window.resize(640, 480);
    window.show();

    QTimer timer;
    QObject::connect(&timer, &QTimer::timeout, &window,
                     QOverload<>::of(&QOpenGLWindow::update));
    timer.start(16);
    return application.exec();
}
