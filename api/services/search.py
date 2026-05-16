"""Full-text and semantic search service (§12).

Full-text: PostgreSQL tsvector with GIN indexes.
Semantic: pgvector cosine similarity — only when llm_embedding_base_url is set
          and the caller requests ?semantic=true.
Hybrid ranking: semantic 60%, fulltext 40% when both available.

Domain filter logic:
  - Tasks, workflows, and principles are filtered by domain when specified.
"""

import uuid
from dataclasses import dataclass

import httpx
import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings
from api.schemas.search import SearchResponse, SearchResult

log = structlog.get_logger(__name__)

_VALID_TYPES = {"principle", "task", "workflow"}

_DEFAULT_TYPES = list(_VALID_TYPES)

# Weights for hybrid scoring
_SEMANTIC_WEIGHT = 0.6
_FULLTEXT_WEIGHT = 0.4


@dataclass
class _TypeConfig:
    record_type: str
    table: str
    fts_expr: str       # PostgreSQL tsvector expression — must match GIN index
    excerpt_col: str
    has_domain: bool    # whether this type has a domain column


# fts_expr values must exactly match the GIN index expressions in the migration.
_TYPE_CONFIGS: list[_TypeConfig] = [
    _TypeConfig(
        "principle", "principles",
        "to_tsvector('english', title || ' ' || summary || ' ' || explanation || ' ' || COALESCE(analogies, ''))",  # noqa: E501
        "summary", True,
    ),
    _TypeConfig(
        "task", "tasks",
        "to_tsvector('english', title || ' ' || outcome || ' ' || COALESCE(software_name, '') || ' ' || COALESCE(software_version, ''))",  # noqa: E501
        "outcome", True,
    ),
    _TypeConfig(
        "workflow", "workflows",
        "to_tsvector('english', title || ' ' || objective)",
        "objective", True,
    ),
]

_CONFIG_BY_TYPE: dict[str, _TypeConfig] = {c.record_type: c for c in _TYPE_CONFIGS}


def _active_configs(
    record_types: list[str] | None,
    domain: str | None,
) -> list[_TypeConfig]:
    """Return configs for requested types, excluding domain-less types when domain filter active."""
    types = set(record_types) if record_types else _VALID_TYPES
    configs = [c for c in _TYPE_CONFIGS if c.record_type in types]
    if domain is not None:
        configs = [c for c in configs if c.has_domain]
    return configs


def _fts_leg(cfg: _TypeConfig, domain: str | None) -> str:
    domain_filter = "AND domain = :domain" if domain is not None else ""
    domain_col = "domain" if cfg.has_domain else "NULL::text"
    # cfg fields come from hardcoded dataclass — not user input.
    return (
        f"""
        SELECT
            '{cfg.record_type}'::text AS record_type,
            id,
            record_id,
            version,
            title,
            status,
            {domain_col} AS domain,
            {cfg.excerpt_col} AS excerpt,
            embedding IS NOT NULL AS has_embedding,
            ts_rank({cfg.fts_expr}, websearch_to_tsquery('english', :q)) AS fts_score
        FROM {cfg.table}
        WHERE status = :status
        {domain_filter}
        AND {cfg.fts_expr} @@ websearch_to_tsquery('english', :q)
    """
    )


async def _get_query_embedding(settings: Settings, query: str) -> list[float] | None:
    """Call the embedding API to vectorise the search query. Returns None on any failure."""
    if not settings.llm_embedding_base_url or not settings.llm_embedding_model:
        return None
    headers: dict[str, str] = {"Content-Type": "application/json"}
    api_key = settings.llm_embedding_api_key.get_secret_value()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{settings.llm_embedding_base_url}/embeddings",
                json={"model": settings.llm_embedding_model, "input": query},
                headers=headers,
                timeout=settings.llm_embedding_timeout_seconds,
            )
            resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]  # type: ignore[no-any-return]
    except Exception as exc:
        log.warning("search_query_embedding_failed", error=str(exc))
        return None


async def _semantic_scores(
    session: AsyncSession,
    configs: list[_TypeConfig],
    query_embedding: list[float],
    domain: str | None,
    status: str,
    candidate_limit: int,
) -> dict[str, float]:
    """Return {record_type:id_str → cosine_similarity} for top semantic matches."""
    vec_str = str(query_embedding)
    scores: dict[str, float] = {}
    for cfg in configs:
        domain_filter = "AND domain = :domain" if domain is not None else ""
        # table comes from a hardcoded dataclass — not user input.
        sql = (
            f"""
            SELECT id, 1 - (embedding <=> :vec::vector) AS sem_score
            FROM {cfg.table}
            WHERE status = :status
            AND embedding IS NOT NULL
            {domain_filter}
            ORDER BY embedding <=> :vec::vector
            LIMIT :lim
        """
        )
        params: dict[str, object] = {"vec": vec_str, "status": status, "lim": candidate_limit}
        if domain:
            params["domain"] = domain
        result = await session.execute(sa.text(sql), params)
        for row in result:
            key = f"{cfg.record_type}:{row.id}"
            scores[key] = float(row.sem_score)
    return scores


async def _semantic_available(session: AsyncSession) -> bool:
    """True if all confirmed records across all types have embeddings."""
    sql = """
        SELECT EXISTS (
            SELECT 1 FROM (
                SELECT embedding FROM principles WHERE status = 'confirmed'
                UNION ALL SELECT embedding FROM tasks WHERE status = 'confirmed'
                UNION ALL SELECT embedding FROM workflows WHERE status = 'confirmed'
            ) AS e
            WHERE embedding IS NULL
            LIMIT 1
        ) AS has_missing
    """
    result = await session.execute(sa.text(sql))
    row = result.one()
    return not bool(row.has_missing)


async def run_search(
    session: AsyncSession,
    settings: Settings,
    q: str,
    record_types: list[str] | None,
    domain: str | None,
    status: str,
    semantic: bool,
    limit: int,
    offset: int,
) -> SearchResponse:
    """Execute search and return a paginated, ranked result set."""
    configs = _active_configs(record_types, domain)
    if not configs:
        return SearchResponse(results=[], total=0, semantic_available=False)

    legs = [_fts_leg(cfg, domain) for cfg in configs]
    union_sql = "\nUNION ALL\n".join(legs)
    params: dict[str, object] = {"q": q, "status": status}
    if domain:
        params["domain"] = domain

    # Count total matching records for pagination metadata
    count_result = await session.execute(
        sa.text(f"SELECT COUNT(*) FROM ({union_sql}) AS _cnt"),
        params,
    )
    total: int = count_result.scalar_one()

    if total == 0:
        return SearchResponse(
            results=[], total=0, semantic_available=await _semantic_available(session)
        )

    # Fetch the page (pre-semantic ordering by fts_score; reranked below if semantic)
    page_result = await session.execute(
        sa.text(
            f"SELECT * FROM ({union_sql}) AS _r ORDER BY fts_score DESC, id LIMIT :lim OFFSET :off"
        ),
        {**params, "lim": limit, "off": offset},
    )
    rows = page_result.mappings().all()

    # Optionally get semantic scores for the page rows
    sem_scores: dict[str, float] = {}
    query_embedding: list[float] | None = None
    if semantic:
        query_embedding = await _get_query_embedding(settings, q)
        if query_embedding is not None:
            # Fetch semantic scores for the IDs already on this page
            # (using candidate_limit = len(rows) * 5 to cover the page with some headroom)
            sem_scores = await _semantic_scores(
                session, configs, query_embedding, domain, status, max(limit * 3, 50)
            )

    results: list[SearchResult] = []
    for row in rows:
        key = f"{row['record_type']}:{row['id']}"
        fts = float(row["fts_score"])
        sem = sem_scores.get(key)

        if sem is not None:
            score = round(_SEMANTIC_WEIGHT * sem + _FULLTEXT_WEIGHT * min(fts, 1.0), 4)
            match_type: str = "hybrid"
        else:
            score = round(fts, 4)
            match_type = "fulltext"

        results.append(
            SearchResult(
                id=uuid.UUID(str(row["id"])),
                record_id=uuid.UUID(str(row["record_id"])),
                record_type=row["record_type"],
                version=row["version"],
                title=row["title"],
                status=row["status"],
                domain=row["domain"],
                match_type=match_type,  # type: ignore[arg-type]
                score=score,
                excerpt=row["excerpt"],
            )
        )

    # Re-sort the page by hybrid score when semantic boosting changed ranking
    if sem_scores:
        results.sort(key=lambda r: r.score, reverse=True)

    return SearchResponse(
        results=results,
        total=total,
        semantic_available=await _semantic_available(session),
    )
