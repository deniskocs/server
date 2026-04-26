"""FB2 / zip с FB2 → связный текст без XML-тегов."""

from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"


def _fb2_body_elements(fb2_text: str) -> list[ET.Element]:
    try:
        root = ET.fromstring(fb2_text)
    except ET.ParseError as e:
        raise RuntimeError(f"Не удалось разобрать FB2 как XML: {e}") from e
    bodies = root.findall(f"{{{FB2_NS}}}body")
    if not bodies:
        bodies = root.findall("body")
    if not bodies:
        raise RuntimeError("В FB2 нет элемента body")
    return bodies


def bodies_plaintext_from_fb2(fb2_text: str) -> str:
    parts: list[str] = []
    for body in _fb2_body_elements(fb2_text):
        xml = ET.tostring(body, encoding="unicode", method="xml")
        soup = BeautifulSoup(xml, "xml")
        text = soup.get_text("\n\n", strip=True)
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def read_first_fb2_from_zip_bytes(data: bytes) -> tuple[str, str]:
    bio = io.BytesIO(data)
    with zipfile.ZipFile(bio) as zf:
        fb2_names = [n for n in zf.namelist() if n.lower().endswith(".fb2")]
        if not fb2_names:
            raise RuntimeError("В архиве нет .fb2")
        inner = sorted(fb2_names)[0]
        raw = zf.read(inner)
    return inner, raw.decode("utf-8", errors="replace")


def bytes_to_plain_text(data: bytes, path_hint: str = "") -> str:
    """
    Принимает сырые байты: .zip с .fb2 внутри или сырой .fb2 (UTF-8 XML).
    """
    path_l = path_hint.lower()
    is_zip = data.startswith(b"PK\x03\x04") or path_l.endswith(".zip")
    if is_zip:
        try:
            _, fb2 = read_first_fb2_from_zip_bytes(data)
        except zipfile.BadZipFile as e:
            raise RuntimeError(f"Не ZIP: {e}") from e
        return bodies_plaintext_from_fb2(fb2)

    text = data.decode("utf-8", errors="replace")
    if "FictionBook" not in text[:4000]:
        raise RuntimeError("Ожидался ZIP с FB2 или XML FictionBook")
    return bodies_plaintext_from_fb2(text)
