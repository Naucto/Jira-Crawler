from crawler import Crawler, CrawlerWorker

from flask import Flask

from gevent.pywsgi import WSGIServer
from gevent import ssl

from loguru import logger as L

import traceback

from typing import Optional


class WebhookListener:
    def __init__(self, crawler: Crawler, host: str='0.0.0.0', port: int=1988, host_cert: Optional[tuple[str, str]]=None):
        self._crawler = crawler
        self._app     = Flask(__name__)

        self._host = host
        self._port = port

        self._host_cert = host_cert

        self._worker = CrawlerWorker(crawler)

        L.info("The listener is available on {}:{}", host, port)

        @self._app.errorhandler(Exception)
        def on_error(exception):
            L.error("Unhandled exception occured: {}", exception)
            L.trace(traceback.format_exc())

            return "", 400

        @self._app.post("/")
        def on_event():
            self._worker.commit(None)
            return "", 200

    def run(self):
        extra_kwargs = {}

        if self._host_cert is None:
            L.warning("No TLS certificate specified, running in HTTP mode")
        else:
            certfile = self._host_cert[0]
            keyfile  = self._host_cert[1]

            L.debug("Using {} as the certificate file", certfile)
            L.debug("Using {} as the key file", keyfile)

            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)

            extra_kwargs["ssl_context"] = ssl_context

        server = WSGIServer(
            (self._host, self._port), # type: ignore
            self._app,
            do_handshake_on_connect=False,
            **extra_kwargs
        )

        server.serve_forever()
