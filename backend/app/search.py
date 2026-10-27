"""Búsqueda difusa con `pg_trgm` sobre nombres y alias, insensible a mayúsculas y acentos."""

from sqlalchemy import ColumnElement, func, select, union_all
from sqlalchemy.orm import Session


def fuzzy_ids(
    session: Session, sources: list[tuple[ColumnElement, ColumnElement]], q: str, limit: int
) -> list[int]:
    """Ids que coinciden con `q` en alguna de las columnas `(id, texto)`, del más parecido al menos.

    Coincide por similitud (`%`, tolera erratas: "daikiri") o por similitud de palabra (`<%`,
    autocompletado: "ron" → "Ron blanco"). Ordena por la mejor similitud de palabra y desempata
    por la similitud global, que pone "Ron" por delante de "Ron blanco".
    """
    query = func.immutable_unaccent(func.lower(q))
    parts = []
    for id_column, text_column in sources:
        text = func.immutable_unaccent(func.lower(text_column))
        parts.append(
            select(
                id_column.label("id"),
                func.word_similarity(query, text).label("word"),
                func.similarity(query, text).label("whole"),
            ).where(query.op("%")(text) | query.op("<%")(text))
        )
    matches = union_all(*parts).subquery()
    return list(
        session.scalars(
            select(matches.c.id)
            .group_by(matches.c.id)
            .order_by(
                func.max(matches.c.word).desc(), func.max(matches.c.whole).desc(), matches.c.id
            )
            .limit(limit)
        )
    )
