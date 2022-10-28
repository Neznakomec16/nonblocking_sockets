import argparse
import selectors
import socket
import logging
import types

from sock_learn.logging_config import FORMAT


logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__file__)
messages = [b"Message 1 from client.", b"Message 2 from client."]


def service_connection(key, mask, selector: selectors.DefaultSelector):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            logger.info(f"Received {recv_data!r} from connection {data.connid}")
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            logger.info(f"Closing connection {data.connid}")
            selector.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            logger.info(f"Sending {data.outb!r} to connection {data.connid}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


def start_connections(host: str, port: int, num_conns: int, selector: selectors.DefaultSelector):
    server_addr = (host, port)
    for i in range(num_conns):
        connid = i + 1
        logger.info(f"Starting connection {connid} to {server_addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(
            connid=connid,
            msg_total=sum(len(m) for m in messages),
            recv_total=0,
            messages=messages.copy(),
            outb=b"",
        )
        selector.register(sock, events, data=data)


def start_listening(selector: selectors.DefaultSelector, timeout: int | None = None):
    with selector:
        while events := selector.select(timeout):
            for key, mask in events:
                service_connection(key, mask, selector)


def cli():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--host', type=str, default='127.0.0.1')
    argument_parser.add_argument('--port', '-p', type=int, default=8888)
    args = argument_parser.parse_args()
    host, port = args.host, args.port

    sel = selectors.DefaultSelector()
    start_connections(host, port, 50, sel)
    start_listening(sel)


if __name__ == '__main__':
    cli()
