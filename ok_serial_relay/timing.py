"""Time synchronization engine"""

import datetime
import logging
import msgspec

import ok_serial_relay.protocol as proto

logger = logging.getLogger(__name__)

TIME_QUERY_INTERVAL = 5.0

class TimeTracker:
    def __init__(
        self, *,
        when: float,
        profile_id: int,
        profile_len: int
    ) -> None:
        self._start_time = when
        self._next_query_time = when  # start immediately
        self._pending_reply: proto.TimeReplyPayload | None = None
        self._profile_id = profile_id
        self._profile_len = profile_len

    def has_payload_to_send(self, *, when: float) -> bool:
        return bool(self._pending_reply or when >= self._next_query_time)

    def get_payload_to_send(self, *, when: float) -> (
        proto.TimeQueryPayload |
        proto.TimeReplyPayload |
        None
    ):
        if self._pending_reply:
            msec = int((when - self._start_time) * 1e3 + 0.5)
            reply = msgspec.structs.replace(self._pending_reply, tx_msec=msec)
            self._pending_reply = None
            return reply

        if when >= self._next_query_time:
            self._next_query_time = max(
                self._next_query_time + TIME_QUERY_INTERVAL, 
                when + TIME_QUERY_INTERVAL - 1
            )
            dt = datetime.datetime.fromtimestamp(when, datetime.timezone.utc)
            return proto.TimeQueryPayload(
                yyyymmdd=int(dt.year * 10000 + dt.month * 100 + dt.day),
                hhmmssmmm=int(
                    dt.hour * 10000000 + dt.minute * 100000 +
                    dt.second * 1000 + dt.microsecond // 1000
                ),
            )

        return None

    def handle_received_query(
        self, query: proto.TimeQueryPayload, *, when: float
    ) -> None:
        self._pending_reply = proto.TimeReplyPayload(
            yyyymmdd=query.yyyymmdd,
            hhmmssmmm=query.hhmmssmmm,
            rx_msec=int((when - self._start_time) * 1e3 + 0.5),
            tx_msec=0,
            profile_id=self._profile_id,
            profile_len=self._profile_len,
        )

    def handle_received_reply(
        self, reply: proto.TimeReplyPayload, *, when: float
    ) -> None:
        # TODO: actual time conversion tracking!!
        pass
