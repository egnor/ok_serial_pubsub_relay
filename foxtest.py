#!/usr/bin/env python3
import foxglove
import logging
import ok_logging_setup
import pathlib
import time

print("Hmmmm?")
ok_logging_setup.install({"OK_LOGGING_LEVEL": "DEBUG"})

logging.info("Starting server")
server = foxglove.start_server()

log_schema = foxglove.Schema(
    name="foxglove.Log",
    encoding="jsonschema",
    data=b"",
    # data=pathlib.Path("Log.json").read_bytes(),
)

log_channel = foxglove.Channel(
    "/hello",
    message_encoding="json",
    schema=log_schema,
)

start_time = time.time()
count = 0
while True:
    logging.debug("Hello...")
    now = time.time()
    elapsed = now - start_time
    message = {
        "timestamp": {"sec": int(elapsed), "nsec": int(elapsed % 1 * 1e9)},
        "level": 2,
        "message": f"Hello, Foxglove! {count}",
        "name": pathlib.Path(__file__).name,
        "file": "",
        "line": 0,
    }
    log_channel.log(message)

    time.sleep(0.3)
    count += 1
