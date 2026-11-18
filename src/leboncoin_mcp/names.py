"""Turns the names people use for categories and places into lbc's enums."""

import difflib
import re
import unicodedata
from collections.abc import Sequence
from enum import Enum

from lbc import Category, Department, Region
from mcp.server.mcpserver.exceptions import ToolError

# Every name maps to the members it may designate: one, or several when shared.
type Aliases[E: Enum] = dict[str, list[E]]


def _key(name: str) -> str:
    """`Côtes-d'Armor`, `cotes darmor` and `COTES_DARMOR` share one key."""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^A-Z0-9]", "", ascii_name.upper())


def same_name(left: str, right: str) -> bool:
    return _key(left) == _key(right)


def _readable(member: Enum) -> str:
    return member.name.replace("_", " ").capitalize()


def _listing(members: Sequence[Enum]) -> str:
    return ", ".join(dict.fromkeys(_readable(member) for member in members))


def _match[E: Enum](kind: str, query: str, aliases: Aliases[E]) -> E:
    """Finds the member a name designates, or explains what may have been meant."""
    meant = aliases.get(_key(query), [])
    if len(meant) == 1:
        return meant[0]
    if meant:
        raise ToolError(f"Several {kind}s are named {query!r}: {_listing(meant)}.")
    close = difflib.get_close_matches(_key(query), list(aliases), n=5, cutoff=0.6)
    suggestions = [member for name in close for member in aliases[name]]
    hint = f" Did you mean: {_listing(suggestions)}?" if suggestions else ""
    raise ToolError(f"Unknown {kind} {query!r}.{hint}")


def _alias[E: Enum](aliases: Aliases[E], name: str, member: E) -> None:
    members = aliases.setdefault(_key(name), [])
    if member not in members:
        members.append(member)


def _category_aliases() -> Aliases[Category]:
    """Each category answers to its full name and to its name within its parent."""
    names = {member.name for member in Category}
    aliases: Aliases[Category] = {_key(member.name): [member] for member in Category}
    for member in Category:
        parents = [p for p in names if member.name.startswith(f"{p}_")]
        if parents:
            short = member.name.removeprefix(f"{max(parents, key=len)}_")
            if _key(short) not in names:
                _alias(aliases, short, member)
    return aliases


CATEGORIES = _category_aliases()

CURRENT_REGIONS: Aliases[Region] = {
    _key(region.name): [region]
    for region in (
        Region.AUVERGNE_RHONE_ALPES,
        Region.BOURGOGNE_FRANCHE_COMTE,
        Region.BRETAGNE,
        Region.CENTRE_VAL_DE_LOIRE,
        Region.CORSE,
        Region.GRAND_EST,
        Region.HAUTS_DE_FRANCE,
        Region.ILE_DE_FRANCE,
        Region.NORMANDIE,
        Region.NOUVELLE_AQUITAINE,
        Region.OCCITANIE,
        Region.PAYS_DE_LA_LOIRE,
        Region.PROVENCE_ALPES_COTE_DAZUR,
        Region.GUADELOUPE,
        Region.MARTINIQUE,
        Region.GUYANE,
        Region.REUNION,
    )
}

# lbc has no department below these regions, which cover exactly the same land.
OVERSEAS_DEPARTMENTS = {
    "971": Region.GUADELOUPE,
    "972": Region.MARTINIQUE,
    "973": Region.GUYANE,
    "974": Region.REUNION,
}
CORSICAN_DEPARTMENTS = {
    _key(name) for name in ("2A", "2B", "Corse-du-Sud", "Haute-Corse")
}


def _department_aliases() -> Aliases[Department | Region]:
    aliases: Aliases[Department | Region] = {}
    for member in Department:
        number = member.value[2]
        for name in (member.name, number, number.zfill(2)):
            _alias(aliases, name, member)
    for number, region in OVERSEAS_DEPARTMENTS.items():
        _alias(aliases, number, region)
        _alias(aliases, region.name, region)
    return aliases


DEPARTMENTS = _department_aliases()


def category(name: str | None) -> Category:
    if name is None:
        return Category.TOUTES_CATEGORIES
    return _match("category", name, CATEGORIES)


def department(name: str) -> Department | Region:
    if _key(name) in CORSICAN_DEPARTMENTS:
        raise ToolError(
            f"Leboncoin cannot search the department {name!r} on its own: "
            "use the region 'Corse', which covers both Corsican departments."
        )
    return _match("department", name, DEPARTMENTS)


def region(name: str) -> Region:
    return _match("region", name, CURRENT_REGIONS)
