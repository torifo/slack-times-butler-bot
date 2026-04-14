from dataclasses import dataclass


@dataclass(slots=True)
class TagOperation:
    add: list[str]
    remove: list[str]
