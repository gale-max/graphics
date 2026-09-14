QT += gui waylandcompositor

TARGET = qt-wayland-smoke-compositor

HEADERS += \
    window.h \
    compositor.h

SOURCES += main.cpp \
    window.cpp \
    compositor.cpp


RESOURCES += qwindow-compositor.qrc

target.path = $$[QT_INSTALL_EXAMPLES]/wayland/qwindow-compositor
INSTALLS += target
