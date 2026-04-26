"""Сборка пути внутри шары без выхода за SMB_ROOT (защита от ..)."""


def normalize_segments(path: str) -> list[str]:
    parts: list[str] = []
    for segment in path.replace("\\", "/").split("/"):
        if not segment or segment == ".":
            continue
        parts.append(segment)
    return parts


def resolve_under_root(root: str, subpath: str) -> str:
    """
    root и subpath — пути относительно шары; возвращает один относительный путь
    с обратными слэшами для UNC (без выхода выше root).
    """
    stack = normalize_segments(root)
    for segment in normalize_segments(subpath):
        if segment == "..":
            if not stack:
                raise ValueError("path escapes configured root")
            stack.pop()
        else:
            stack.append(segment)
    return "\\".join(stack)


def to_unc(host: str, share: str, rel_parts: str) -> str:
    rel = rel_parts.replace("/", "\\").strip("\\")
    if rel:
        return rf"\\{host}\{share}\{rel}"
    return rf"\\{host}\{share}"
