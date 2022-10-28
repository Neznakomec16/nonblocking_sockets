import argparse
import logging
import socket
import selectors
import types

from sock_learn.logging_config import FORMAT

logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__file__)


def accept_wrapper(sock, selector: selectors.DefaultSelector):
    conn, addr = sock.accept()  # Should be ready to read
    logger.info(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    selector.register(conn, events, data=data)


def service_connection(key: selectors.SelectorKey, mask: int, selector: selectors.DefaultSelector):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data + b' echoed'
        else:
            logger.info(f"Closing connection to {data.addr}")
            selector.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            logger.info(f"Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


def start_listening(selector: selectors.DefaultSelector, timeout: int | None = None):
    with selector:
        while events := selector.select(timeout):
            for key, mask in events:
                if key.data is not None:
                    service_connection(key, mask, selector)
                else:
                    accept_wrapper(key.fileobj, selector)


def cli():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--host', type=str, default='127.0.0.1')
    argument_parser.add_argument('--port', '-p', type=int, default=8888)
    args = argument_parser.parse_args()
    host, port = args.host, args.port

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen()
    sock.setblocking(False)

    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_READ, data=None)

    logger.info(f'Starting server at {host}:{port}')
    start_listening(sel)


if __name__ == '__main__':
    cli()
