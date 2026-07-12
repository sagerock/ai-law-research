from dataclasses import dataclass
from typing import Awaitable, Callable, Optional


OpinionReader = Callable[[str], Awaitable[Optional[str]]]


@dataclass(frozen=True)
class OpinionResult:
    text: Optional[str]
    source: Optional[str]


def is_courtlistener_id(case_id: str) -> bool:
    return str(case_id).isdigit()


async def load_opinion_text(
    case_id: str,
    database_content: Optional[str],
    read_s3: OpinionReader,
    fetch_courtlistener: Optional[OpinionReader] = None,
) -> OpinionResult:
    if database_content and database_content.strip():
        return OpinionResult(database_content, "postgres")

    s3_text = await read_s3(case_id)
    if s3_text and s3_text.strip():
        return OpinionResult(s3_text, "s3")

    if fetch_courtlistener and is_courtlistener_id(case_id):
        courtlistener_text = await fetch_courtlistener(case_id)
        if courtlistener_text and courtlistener_text.strip():
            return OpinionResult(courtlistener_text, "courtlistener")

    return OpinionResult(None, None)
