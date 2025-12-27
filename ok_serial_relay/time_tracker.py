"""Basic embedded/unix time synchronization engine"""

import datetime
import logging

from ok_serial_relay.line_types import TimeQueryPayload, TimeReplyPayload

logger = logging.getLogger(__name__)

TIME_QUERY_INTERVAL = 5.0


class TimeTracker:
    def __init__(
        self, *, when: float, profile_id: int, profile_len: int
    ) -> None:
        self._start_time = when
        self._next_query_time = when  # start immediately
        self._pending_reply: TimeReplyPayload | None = None

    def has_payload_to_send(self, *, when: float) -> bool:
        return bool(self._pending_reply or when >= self._next_query_time)

    def get_payload_to_send(
        self, *, when: float
    ) -> TimeQueryPayload | TimeReplyPayload | None:
        if self._pending_reply:
            msec = int((when - self._start_time) * 1e3 + 0.5)
            reply, self._pending_reply = self._pending_reply, None
            reply.tx_msec = msec
            logger.debug("To send: %s", reply)
            return reply

        if when >= self._next_query_time:
            self._next_query_time = max(
                self._next_query_time + TIME_QUERY_INTERVAL,
                when + TIME_QUERY_INTERVAL - 1,
            )
            dt = datetime.datetime.fromtimestamp(when, datetime.timezone.utc)
            query = TimeQueryPayload(
                yyyymmdd=int(dt.year * 10000 + dt.month * 100 + dt.day),
                hhmmssmmm=int(
                    dt.hour * 10000000
                    + dt.minute * 100000
                    + dt.second * 1000
                    + dt.microsecond // 1000
                ),
            )
            logger.debug("To send: %s", query)
            return query

        return None

    def on_query_received(
        self, query: TimeQueryPayload, *, when: float
    ) -> None:
        logger.debug("Received: %s", query)
        self._pending_reply = TimeReplyPayload(
            yyyymmdd=query.yyyymmdd,
            hhmmssmmm=query.hhmmssmmm,
            rx_msec=int((when - self._start_time) * 1e3 + 0.5),
            tx_msec=0,
        )

    def on_reply_received(
        self, reply: TimeReplyPayload, *, when: float
    ) -> None:
        logger.debug("Received: %s", reply)
        # TODO: actual time conversion tracking!!
        pass

    def try_from_msec(self, msec: int) -> float:
        # TODO: actual time conversion!!
        return 0.0

    def try_to_msec(self, unixtime: float) -> int:
        # TODO: actual time conversion!!
        return 0
