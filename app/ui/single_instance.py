"""Forward web links to the running desktop without opening a second manager."""
import hashlib
from PySide6.QtCore import QObject, QLockFile, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    received = Signal(str)

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        directory.mkdir(parents=True, exist_ok=True)
        self.name = 'bbmod-' + hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:20]
        self.lock = QLockFile(str(directory / 'desktop.lock'))
        self.server = QLocalServer(self)
        self.sockets = set()
        self.server.newConnection.connect(self._accept)

    def start(self, message=''):
        if not self.lock.tryLock(100):
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            if not socket.waitForConnected(2000):
                raise OSError('BBMOD 正在启动或忙碌，请稍后重试网页链接。')
            socket.write((message + '\n').encode())
            if not socket.waitForBytesWritten(2000):
                raise OSError('未能将链接交给正在运行的 BBMOD，请重试。')
            socket.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            self.lock.unlock()
            raise OSError('无法启动 BBMOD 本地链接接收器。')
        return True

    def _accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self.sockets.add(socket)
            buffer = bytearray()

            def read(sock=socket, data=buffer):
                data.extend(bytes(sock.readAll()))
                if len(data) > 1024:
                    sock.abort()
                elif b'\n' in data:
                    try:
                        self.received.emit(data.split(b'\n', 1)[0].decode('utf-8'))
                    except UnicodeDecodeError:
                        pass
                    sock.disconnectFromServer()

            socket.readyRead.connect(read)
            socket.disconnected.connect(lambda sock=socket: (self.sockets.discard(sock), sock.deleteLater()))
            read()
